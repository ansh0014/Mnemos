"""MCP Gateway & HTTP route registration for Stage 1 Prime Agent."""

from __future__ import annotations

import asyncio
from typing import Any

from mnemos_services.common.mcp_gateway import AgentRole, MCPGateway

from ..handlers.prime_handler import PrimeHandler
from ..models.schemas import PrimeRequest


def register_prime_tools(gateway: MCPGateway, handler: PrimeHandler | None = None) -> PrimeHandler:
    """Register Prime Agent tools onto the shared MCP Gateway."""
    prime = handler or PrimeHandler()

    gateway.register_tool(
        name="get_chapter_summary",
        description="Summarize the active chapter into a concise engineering problem statement.",
        input_schema={
            "type": "object",
            "properties": {
                "chapter_title": {"type": "string"},
                "chapter_text": {"type": "string"},
            },
            "required": ["chapter_title", "chapter_text"],
        },
        allowed_roles={AgentRole.PRIME},
        tags={"stage:prime"},
        handler=prime.get_chapter_summary,
    )

    async def _dialogue(chapter_title: str, chapter_text: str, concept_id: str | None = None) -> dict[str, Any]:
        return await prime.generate_dialogue_briefing(
            PrimeRequest(chapter_title=chapter_title, chapter_text=chapter_text, concept_id=concept_id)
        )

    gateway.register_tool(
        name="generate_dialogue_briefing",
        description="Generate a 60-second Ada & Theo architectural dialogue framing the chapter.",
        input_schema={
            "type": "object",
            "properties": {
                "chapter_title": {"type": "string"},
                "chapter_text": {"type": "string"},
                "concept_id": {"type": "string"},
            },
            "required": ["chapter_title", "chapter_text"],
        },
        allowed_roles={AgentRole.PRIME},
        tags={"stage:prime"},
        handler=_dialogue,
    )
    return prime


def build_http_routes(handler: PrimeHandler | None = None) -> dict[str, Any]:
    prime = handler or PrimeHandler()
    return {
        "/prime/summary": lambda body: prime.get_chapter_summary(
            body["chapter_title"], body["chapter_text"]
        ),
        "/prime/dialogue": lambda body: asyncio.run(
            prime.generate_dialogue_briefing(
                PrimeRequest(
                    chapter_title=body["chapter_title"],
                    chapter_text=body["chapter_text"],
                    concept_id=body.get("concept_id"),
                )
            )
        ),
    }
