"""Unified Mnemos Cognitive & Verification Services Runtime.

Wires all 6 Python services (``ingestion-engine``, ``memory-engine``, ``agent-prime``,
``agent-copilot``, ``agent-socratic``, ``agent-challenge``) onto a single ``MCPGateway``
and exposes unified REST + JSON-RPC 2.0 routes for Go gateway or Web UI integration.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from mnemos_services.agent_challenge.handlers.challenge_handler import ChallengeHandler
from mnemos_services.agent_challenge.routes.api import (
    build_http_routes as build_challenge_routes,
    register_challenge_tools,
)
from mnemos_services.agent_copilot.handlers.copilot_handler import CoPilotHandler
from mnemos_services.agent_copilot.routes.api import (
    build_http_routes as build_copilot_routes,
    register_copilot_tools,
)
from mnemos_services.agent_prime.handlers.prime_handler import PrimeHandler
from mnemos_services.agent_prime.routes.api import (
    build_http_routes as build_prime_routes,
    register_prime_tools,
)
from mnemos_services.agent_socratic.handlers.socratic_handler import SocraticHandler
from mnemos_services.agent_socratic.routes.api import (
    build_http_routes as build_socratic_routes,
    register_socratic_tools,
)
from mnemos_services.common.mcp_gateway import AgentRole, MCPGateway, make_http_server
from mnemos_services.ingestion_engine.graph.knowledge_graph import get_active_curriculum
from mnemos_services.ingestion_engine.parser.book_parser import ingest_book_file, parse_markdown_book
from mnemos_services.memory_engine.episodic.store import CognitiveMemoryStore
from mnemos_services.memory_engine.semantic.graph_memory import SemanticGraphMemory
from mnemos_services.memory_engine.vector.index import LocalVectorIndex


@dataclass
class MnemosServicesRuntime:
    gateway: MCPGateway
    memory_store: CognitiveMemoryStore
    semantic_memory: SemanticGraphMemory
    vector_index: LocalVectorIndex
    prime: PrimeHandler
    copilot: CoPilotHandler
    socratic: SocraticHandler
    challenge: ChallengeHandler
    http_routes: dict[str, Any]


def _register_memory_and_ingestion_tools(
    gateway: MCPGateway,
    memory_store: CognitiveMemoryStore,
    semantic_memory: SemanticGraphMemory,
) -> None:
    gateway.register_tool(
        name="get_due_fsrs_cards",
        description="Fetch due FSRS-4.5 flashcards ready for review.",
        input_schema={"type": "object", "properties": {"limit": {"type": "integer"}}},
        allowed_roles={AgentRole.REMEMBER},
        tags={"stage:remember"},
        handler=lambda limit=20: {"cards": memory_store.get_due_fsrs_cards(limit=limit)},
    )
    gateway.register_tool(
        name="record_fsrs_review",
        description="Schedule next FSRS-4.5 review interval for a flashcard rating (1-4).",
        input_schema={
            "type": "object",
            "properties": {"card_id": {"type": "string"}, "rating": {"type": "integer"}},
            "required": ["card_id", "rating"],
        },
        allowed_roles={AgentRole.REMEMBER},
        tags={"stage:remember"},
        handler=memory_store.schedule_fsrs_review,
    )
    gateway.register_tool(
        name="create_atomic_card",
        description="Create an atomic spaced-repetition flashcard linked to a concept.",
        input_schema={
            "type": "object",
            "properties": {"concept_id": {"type": "string"}, "front": {"type": "string"}, "back": {"type": "string"}},
            "required": ["concept_id", "front", "back"],
        },
        allowed_roles={AgentRole.REMEMBER},
        tags={"stage:remember"},
        handler=memory_store.create_atomic_card,
    )
    gateway.register_tool(
        name="where_does_this_fit",
        description="Locate any engineering buzzword inside the Grand Scheme Knowledge Graph.",
        input_schema={
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
        allowed_roles={AgentRole.PRIME, AgentRole.READ, AgentRole.RECALL, AgentRole.CHALLENGE},
        tags={"compass", "stage:read"},
        handler=semantic_memory.where_does_this_fit,
    )


def create_integrated_runtime(
    db_path: str = ":memory:",
    model: Any = None,
) -> MnemosServicesRuntime:
    """Instantiate all 6 services sharing unified memory, knowledge graph, and MCP gateway."""
    gateway = MCPGateway()
    memory_store = CognitiveMemoryStore(db_path=db_path)
    curriculum = get_active_curriculum()
    semantic_memory = SemanticGraphMemory(curriculum=curriculum)

    vector_index = LocalVectorIndex()
    vector_index.add_documents(
        [
            {
                "id": node["id"],
                "title": node["title"],
                "text": f"{node['title']}. {node['summary']} {node['why_it_exists']} {' '.join(node.get('tradeoffs', []))}",
            }
            for node in curriculum.get("nodes", [])
        ]
    )

    prime = register_prime_tools(gateway, PrimeHandler(semantic_memory=semantic_memory, model=model))
    copilot = register_copilot_tools(
        gateway, CoPilotHandler(semantic_memory=semantic_memory, episodic_memory=memory_store, model=model)
    )
    socratic = register_socratic_tools(
        gateway,
        SocraticHandler(
            memory_store=memory_store,
            semantic_memory=semantic_memory,
            vector_index=vector_index,
            model=model,
        ),
    )
    challenge = register_challenge_tools(
        gateway, ChallengeHandler(memory_store=memory_store, semantic_memory=semantic_memory)
    )
    _register_memory_and_ingestion_tools(gateway, memory_store, semantic_memory)

    http_routes: dict[str, Any] = {
        "/ingestion/parse-markdown": lambda body: parse_markdown_book(
            body["markdown_text"], body.get("book_title", "Untitled Book")
        ),
        "/ingestion/parse-file": lambda body: ingest_book_file(body["book_path"], body.get("out_dir")),
        "/memory/compass": lambda body: semantic_memory.where_does_this_fit(body["query"]),
        "/memory/prerequisites": lambda body: {
            "concept_id": body["concept_id"],
            "prerequisites": semantic_memory.get_prerequisites(body["concept_id"]),
        },
        "/memory/episodic-failures": lambda body: {
            "failures": memory_store.get_recent_failures(
                user_id=body.get("user_id", "default"),
                concept_id=body.get("concept_id"),
            )
        },
        "/memory/fsrs/due": lambda body: {
            "cards": memory_store.get_due_fsrs_cards(limit=int(body.get("limit", 20)))
        },
        "/memory/fsrs/review": lambda body: memory_store.schedule_fsrs_review(
            body["card_id"], int(body["rating"])
        ),
        # Also allow JSON-RPC 2.0 `method: "where_does_this_fit"` etc.
        "where_does_this_fit": lambda params: semantic_memory.where_does_this_fit(params["query"]),
    }
    http_routes.update(build_prime_routes(prime))
    http_routes.update(build_copilot_routes(copilot))
    http_routes.update(build_socratic_routes(socratic))
    http_routes.update(build_challenge_routes(challenge))

    return MnemosServicesRuntime(
        gateway=gateway,
        memory_store=memory_store,
        semantic_memory=semantic_memory,
        vector_index=vector_index,
        prime=prime,
        copilot=copilot,
        socratic=socratic,
        challenge=challenge,
        http_routes=http_routes,
    )


def main() -> None:
    """Boot the unified Python cognitive & verification backend server."""
    runtime = create_integrated_runtime(db_path="learner_memory.db")
    server = make_http_server("127.0.0.1", 8090, runtime.http_routes, service_name="mnemos-python-services")
    print("Mnemos Python services listening on http://127.0.0.1:8090")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()
        runtime.memory_store.close()


if __name__ == "__main__":
    main()
