"""MCP Gateway & HTTP route registration for Stage 3 Socratic Diagnostic Agent."""

from __future__ import annotations

import asyncio
from typing import Any

from mnemos_services.common.mcp_gateway import AgentRole, MCPGateway

from ..handlers.socratic_handler import SocraticHandler
from ..models.schemas import SocraticRequest


def register_socratic_tools(gateway: MCPGateway, handler: SocraticHandler | None = None) -> SocraticHandler:
    """Register Socratic Recall tools onto the shared MCP Gateway."""
    socratic = handler or SocraticHandler()

    gateway.register_tool(
        name="query_book_ground_truth",
        description="Search indexed book ground truth passages to verify learner claims.",
        input_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "top_k": {"type": "integer"},
            },
            "required": ["query"],
        },
        allowed_roles={AgentRole.RECALL},
        tags={"stage:recall"},
        handler=socratic.query_book_ground_truth,
    )

    gateway.register_tool(
        name="get_learner_misconceptions",
        description="Fetch active diagnosed misconceptions for a learner and concept.",
        input_schema={
            "type": "object",
            "properties": {
                "concept_id": {"type": "string"},
                "user_id": {"type": "string"},
            },
        },
        allowed_roles={AgentRole.RECALL},
        tags={"stage:recall"},
        handler=socratic.get_learner_misconceptions,
    )

    gateway.register_tool(
        name="log_misconception_resolution",
        description="Mark unresolved misconceptions for a concept as resolved.",
        input_schema={
            "type": "object",
            "properties": {
                "concept_id": {"type": "string"},
                "user_id": {"type": "string"},
            },
            "required": ["concept_id"],
        },
        allowed_roles={AgentRole.RECALL},
        tags={"stage:recall"},
        handler=socratic.log_misconception_resolution,
    )

    async def _evaluate(
        concept_id: str,
        question: str,
        answer: str,
        core_points: list[str] | None = None,
        invariant_points: list[str] | None = None,
        tradeoff_points: list[str] | None = None,
        user_id: str = "default",
    ) -> dict[str, Any]:
        return await socratic.evaluate_socratic_recall(
            SocraticRequest(
                concept_id=concept_id,
                question=question,
                answer=answer,
                core_points=core_points or [],
                invariant_points=invariant_points or [],
                tradeoff_points=tradeoff_points or [],
                user_id=user_id,
            )
        )

    gateway.register_tool(
        name="evaluate_socratic_recall",
        description="Evaluate recall against weighted rubric, detect misconceptions, and emit one probing question.",
        input_schema={
            "type": "object",
            "properties": {
                "concept_id": {"type": "string"},
                "question": {"type": "string"},
                "answer": {"type": "string"},
                "core_points": {"type": "array"},
                "invariant_points": {"type": "array"},
                "tradeoff_points": {"type": "array"},
                "user_id": {"type": "string"},
            },
            "required": ["concept_id", "question", "answer"],
        },
        allowed_roles={AgentRole.RECALL},
        tags={"stage:recall"},
        handler=_evaluate,
    )
    return socratic


def build_http_routes(handler: SocraticHandler | None = None) -> dict[str, Any]:
    socratic = handler or SocraticHandler()
    return {
        "/socratic/ground-truth": lambda body: socratic.query_book_ground_truth(
            body["query"], int(body.get("top_k", 3))
        ),
        "/socratic/misconceptions": lambda body: socratic.get_learner_misconceptions(
            body.get("concept_id"), body.get("user_id", "default")
        ),
        "/socratic/evaluate": lambda body: asyncio.run(
            socratic.evaluate_socratic_recall(
                SocraticRequest(
                    concept_id=body["concept_id"],
                    question=body["question"],
                    answer=body["answer"],
                    core_points=body.get("core_points", []),
                    invariant_points=body.get("invariant_points", []),
                    tradeoff_points=body.get("tradeoff_points", []),
                    user_id=body.get("user_id", "default"),
                )
            )
        ),
    }
