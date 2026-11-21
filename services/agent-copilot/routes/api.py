"""MCP Gateway & HTTP route registration for Stage 2 Active Reading Co-Pilot."""

from __future__ import annotations

import asyncio
from typing import Any

from mnemos_services.common.mcp_gateway import AgentRole, MCPGateway

from ..handlers.copilot_handler import CoPilotHandler


def register_copilot_tools(gateway: MCPGateway, handler: CoPilotHandler | None = None) -> CoPilotHandler:
    """Register Reading Co-Pilot tools onto the shared MCP Gateway."""
    copilot = handler or CoPilotHandler()

    gateway.register_tool(
        name="get_active_section_text",
        description="Inspect active section context enriched with prerequisites and recent episodic failures.",
        input_schema={
            "type": "object",
            "properties": {
                "section_text": {"type": "string"},
                "concept_id": {"type": "string"},
                "user_id": {"type": "string"},
            },
            "required": ["section_text"],
        },
        allowed_roles={AgentRole.READ},
        tags={"stage:read"},
        handler=copilot.get_active_section_text,
    )

    gateway.register_tool(
        name="lookup_prerequisite_term",
        description="Resolve an unfamiliar engineering term onto the Grand Scheme Knowledge Graph.",
        input_schema={
            "type": "object",
            "properties": {"term": {"type": "string"}},
            "required": ["term"],
        },
        allowed_roles={AgentRole.READ},
        tags={"stage:read"},
        handler=copilot.lookup_prerequisite_term,
    )

    gateway.register_tool(
        name="generate_code_example",
        description="Synthesize a 15-20 line runnable code example for the active passage.",
        input_schema={
            "type": "object",
            "properties": {
                "paragraph": {"type": "string"},
                "language": {"type": "string", "enum": ["python", "typescript", "go"]},
                "concept_id": {"type": "string"},
                "user_id": {"type": "string"},
            },
            "required": ["paragraph"],
        },
        allowed_roles={AgentRole.READ},
        tags={"stage:read"},
        handler=copilot.generate_code_example,
    )

    gateway.register_tool(
        name="get_production_war_story",
        description="Fetch a real-world post-mortem showing how the concept fails in production.",
        input_schema={
            "type": "object",
            "properties": {"concept_or_paragraph": {"type": "string"}},
            "required": ["concept_or_paragraph"],
        },
        allowed_roles={AgentRole.READ},
        tags={"stage:read"},
        handler=copilot.get_production_war_story,
    )
    return copilot


def build_http_routes(handler: CoPilotHandler | None = None) -> dict[str, Any]:
    copilot = handler or CoPilotHandler()
    return {
        "/copilot/section": lambda body: copilot.get_active_section_text(
            body["section_text"], body.get("concept_id"), body.get("user_id", "default")
        ),
        "/copilot/lookup": lambda body: copilot.lookup_prerequisite_term(body["term"]),
        "/copilot/code": lambda body: asyncio.run(
            copilot.generate_code_example(
                body["paragraph"],
                body.get("language", "python"),
                body.get("concept_id"),
                body.get("user_id", "default"),
            )
        ),
        "/copilot/war-story": lambda body: asyncio.run(
            copilot.get_production_war_story(body["concept_or_paragraph"])
        ),
        "/copilot/devils-advocate": lambda body: asyncio.run(
            copilot.devils_advocate_tradeoffs(body["paragraph"], body.get("concept_id"))
        ),
        "/copilot/margin-notes": lambda body: {
            "notes": copilot.generate_margin_notes(body["section_text"], int(body.get("max_notes", 2)))
        },
    }
