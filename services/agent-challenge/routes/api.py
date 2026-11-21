"""MCP Gateway & HTTP route registration for Stage 4 Challenge Verification Sandbox."""

from __future__ import annotations

from typing import Any

from mnemos_services.common.mcp_gateway import AgentRole, MCPGateway

from ..handlers.challenge_handler import ChallengeHandler


def register_challenge_tools(gateway: MCPGateway, handler: ChallengeHandler | None = None) -> ChallengeHandler:
    """Register Challenge Sandbox tools onto the shared MCP Gateway."""
    challenge = handler or ChallengeHandler()

    gateway.register_tool(
        name="configure_simulation_scenario",
        description="Initialize or resume a 5-Beat discovery lab at its current unlocked beat.",
        input_schema={
            "type": "object",
            "properties": {"lab_id": {"type": "string"}, "user_id": {"type": "string"}},
            "required": ["lab_id"],
        },
        allowed_roles={AgentRole.CHALLENGE},
        tags={"stage:harness"},
        handler=challenge.configure_simulation_scenario,
    )

    gateway.register_tool(
        name="inject_simulation_fault",
        description="Run learner code under deterministic fault injection and return SimulationTrace frames.",
        input_schema={
            "type": "object",
            "properties": {
                "lab_id": {"type": "string"},
                "beat": {"type": "integer"},
                "user_code": {"type": "string"},
                "user_id": {"type": "string"},
            },
            "required": ["lab_id", "beat", "user_code"],
        },
        allowed_roles={AgentRole.CHALLENGE},
        tags={"stage:harness"},
        handler=lambda lab_id, beat, user_code, user_id="default": challenge.run_beat_verification(
            lab_id=lab_id, beat=beat, user_code=user_code, mode="stress_simulation", user_id=user_id
        ),
    )

    gateway.register_tool(
        name="run_beat_verification",
        description="Run behavioral unit tests or stress verification for a specific lab beat.",
        input_schema={
            "type": "object",
            "properties": {
                "lab_id": {"type": "string"},
                "beat": {"type": "integer"},
                "user_code": {"type": "string"},
                "mode": {"type": "string", "enum": ["unit_tests", "stress_simulation"]},
                "user_id": {"type": "string"},
            },
            "required": ["lab_id", "beat", "user_code"],
        },
        allowed_roles={AgentRole.CHALLENGE},
        tags={"stage:harness"},
        handler=challenge.run_beat_verification,
    )

    gateway.register_tool(
        name="submit_diagnosis",
        description="Submit a Beat 3 intuitive root-cause diagnosis option to unlock Beat 4.",
        input_schema={
            "type": "object",
            "properties": {
                "lab_id": {"type": "string"},
                "option_id": {"type": "string"},
                "user_id": {"type": "string"},
            },
            "required": ["lab_id", "option_id"],
        },
        allowed_roles={AgentRole.CHALLENGE},
        tags={"stage:harness"},
        handler=challenge.submit_diagnosis,
    )

    gateway.register_tool(
        name="extract_concept_nodes",
        description="Retrieve the Knowledge Graph node and prerequisite/downstream links for a lab.",
        input_schema={
            "type": "object",
            "properties": {"lab_id": {"type": "string"}},
            "required": ["lab_id"],
        },
        allowed_roles={AgentRole.CHALLENGE},
        tags={"stage:harness"},
        handler=challenge.extract_concept_nodes,
    )
    return challenge


def build_http_routes(handler: ChallengeHandler | None = None) -> dict[str, Any]:
    challenge = handler or ChallengeHandler()
    return {
        "/challenge/configure": lambda body: challenge.configure_simulation_scenario(
            body["lab_id"], body.get("user_id", "default")
        ),
        "/challenge/beat": lambda body: challenge.get_beat_spec(body["lab_id"], body["beat"]),
        "/challenge/verify": lambda body: challenge.run_beat_verification(
            body["lab_id"],
            body["beat"],
            body["user_code"],
            body.get("mode", "unit_tests"),
            body.get("user_id", "default"),
        ),
        "/challenge/diagnose": lambda body: challenge.submit_diagnosis(
            body["lab_id"], body["option_id"], body.get("user_id", "default")
        ),
        "/challenge/concepts": lambda body: challenge.extract_concept_nodes(body["lab_id"]),
    }
