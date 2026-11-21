"""Mnemos MCP Gateway, Circuit Breaker, and lightweight HTTP/JSON-RPC server wrapper.

Implements the Control Plane Tool Registry, Data Plane Proxy Router, Role-Scoped
Access Matrix ('Discovery != Exposure'), and DeepMind Response Field Projection
from ``architecture.md`` Section 10 and ``left.md`` Task 1.
"""

from __future__ import annotations

import inspect
import json
import logging
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from enum import Enum
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from .optimizer import project_response_fields, prune_tool_schemas

logger = logging.getLogger("mnemos.mcp_gateway")


class AgentRole(str, Enum):
    ORCHESTRATOR = "orchestrator"
    PRIME = "prime_agent"
    READ = "read_copilot"
    RECALL = "socratic_recall"
    CHALLENGE = "challenge_orchestrator"
    REMEMBER = "remember_agent"


@dataclass
class CircuitBreakerState:
    failure_threshold: int = 3
    reset_timeout_s: float = 15.0
    failures: int = 0
    opened_at: float | None = None

    def allow_request(self, now: float | None = None) -> bool:
        if self.opened_at is None:
            return True
        current = time.monotonic() if now is None else now
        if current - self.opened_at >= self.reset_timeout_s:
            # Half-open transition: allow one probe and reset count.
            self.opened_at = None
            self.failures = 0
            return True
        return False

    def record_success(self) -> None:
        self.failures = 0
        self.opened_at = None

    def record_failure(self, now: float | None = None) -> None:
        self.failures += 1
        if self.failures >= self.failure_threshold:
            self.opened_at = time.monotonic() if now is None else now


@dataclass
class MCPToolDefinition:
    name: str
    description: str
    input_schema: dict[str, Any]
    allowed_roles: set[AgentRole]
    handler: Callable[..., Any | Awaitable[Any]]
    tags: set[str] = field(default_factory=set)
    enabled: bool = True
    projection_fields: list[str] | None = None


class MCPGateway:
    """Central MCP Gateway handling Control Plane Discovery and Data Plane Routing."""

    def __init__(self) -> None:
        self._registry: dict[str, MCPToolDefinition] = {}
        self._breakers: dict[str, CircuitBreakerState] = {}

    def register_tool(
        self,
        name: str,
        description: str,
        input_schema: dict[str, Any],
        allowed_roles: set[AgentRole],
        handler: Callable[..., Any | Awaitable[Any]],
        projection_fields: list[str] | None = None,
        tags: set[str] | None = None,
    ) -> None:
        """Register a backend service tool into the Control Plane Registry."""
        self._registry[name] = MCPToolDefinition(
            name=name,
            description=description,
            input_schema=input_schema,
            allowed_roles=set(allowed_roles),
            handler=handler,
            tags=set(tags or ()),
            enabled=True,
            projection_fields=projection_fields,
        )
        self._breakers.setdefault(name, CircuitBreakerState())

    def discover_tools_by_tag(self, tag: str) -> list[str]:
        """Intent-based capability discovery by semantic tag without exposing schemas."""
        return [t.name for t in self._registry.values() if t.enabled and tag in t.tags]

    def get_scoped_tools(self, role: AgentRole, compact: bool = True) -> dict[str, Any]:
        """Return ONLY tools authorized for ``role``, pruned via DeepMind optimizer."""
        raw_tools = [
            {
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.input_schema,
                "allowed_roles": sorted(r.value for r in tool.allowed_roles),
            }
            for tool in self._registry.values()
            if tool.enabled
        ]
        return prune_tool_schemas(raw_tools, role.value, compact=compact)

    async def invoke_tool(
        self,
        caller_role: AgentRole,
        tool_name: str,
        arguments: dict[str, Any] | None = None,
        projection: list[str] | None = None,
    ) -> dict[str, Any]:
        """Data Plane Execution Router with Role Scoping, Circuit Breaker, and Field Projection."""
        tool = self._registry.get(tool_name)
        if not tool or not tool.enabled:
            raise ValueError(f"Tool '{tool_name}' not found or disabled.")

        if caller_role not in tool.allowed_roles and caller_role != AgentRole.ORCHESTRATOR:
            raise PermissionError(f"Agent '{caller_role.value}' unauthorized for '{tool_name}'.")

        breaker = self._breakers[tool_name]
        if not breaker.allow_request():
            return {"status": "circuit_open", "error": f"Circuit open for tool '{tool_name}'."}

        try:
            raw = tool.handler(**(arguments or {}))
            if inspect.isawaitable(raw):
                raw = await raw
            breaker.record_success()
        except Exception as exc:
            breaker.record_failure()
            logger.exception("Tool execution failed for %s: %s", tool_name, exc)
            return {"status": "failed", "error": str(exc)}

        fields_to_project = projection if projection is not None else tool.projection_fields
        projected = project_response_fields(raw, fields_to_project)
        return {"status": "success", "data": projected}


def make_http_server(
    host: str,
    port: int,
    routes: dict[str, Callable[[dict[str, Any]], dict[str, Any]]],
    service_name: str,
) -> ThreadingHTTPServer:
    """Create a zero-dependency REST + JSON-RPC 2.0 HTTP server for a microservice."""

    class Handler(BaseHTTPRequestHandler):
        def _send_json(self, status: int, body: dict[str, Any]) -> None:
            encoded = json.dumps(body).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

        def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
            return  # keep test/CLI logs clean

        def do_GET(self) -> None:  # noqa: N802
            if self.path == "/health":
                self._send_json(200, {"service": service_name, "status": "ok", "routes": sorted(routes)})
                return
            self._send_json(404, {"error": f"Unknown GET path: {self.path}"})

        def do_POST(self) -> None:  # noqa: N802
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length) if length > 0 else b"{}"
            try:
                payload = json.loads(raw.decode("utf-8"))
            except json.JSONDecodeError as exc:
                self._send_json(400, {"error": f"Invalid JSON: {exc}"})
                return

            if self.path == "/rpc":
                method = payload.get("method")
                params = payload.get("params") or {}
                rpc_id = payload.get("id")
                fn = routes.get(str(method))
                if not fn:
                    self._send_json(404, {"jsonrpc": "2.0", "id": rpc_id, "error": f"Unknown method {method}"})
                    return
                try:
                    result = fn(params)
                    self._send_json(200, {"jsonrpc": "2.0", "id": rpc_id, "result": result})
                except Exception as exc:
                    self._send_json(500, {"jsonrpc": "2.0", "id": rpc_id, "error": str(exc)})
                return

            fn = routes.get(self.path)
            if not fn:
                self._send_json(404, {"error": f"Unknown route: {self.path}"})
                return
            try:
                self._send_json(200, fn(payload))
            except Exception as exc:
                self._send_json(500, {"error": str(exc)})

    return ThreadingHTTPServer((host, port), Handler)
