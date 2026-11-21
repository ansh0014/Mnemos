"""Data contracts for Stage 4 Verification Sandbox & 5-Beat Intuitive Discovery Engine.

Mirrors the general, book-agnostic schemas in ``/home/habanera/Documents/Projects/sat-hackathon/doc.md``
Section 5.3 plus the deterministic simulation traces in ``Mnemos/architecture.md`` Section 3.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

LabBeatNumber = Literal[1, 2, 3, 4, 5]
ShimId = Literal["clock", "storage", "network", "hash", "memory"]
VisualizerPrimitiveType = Literal["timeline_stream", "state_xray", "topology_graph", "metric_gauge"]


@dataclass
class DiagnosisOption:
    id: str
    label: str
    is_correct: bool
    feedback: str


@dataclass
class DiagnosisPrompt:
    question: str
    options: list[DiagnosisOption]


@dataclass
class UnitTestSpec:
    id: str
    name: str
    description: str
    min_beat: Literal[1, 4]
    socratic_hint: str


@dataclass
class LabBeatSpec:
    beat: LabBeatNumber
    title: str
    narrative: str
    instructions: str
    starter_code: str | None = None
    diagnosis: DiagnosisPrompt | None = None
    stress_scenario_id: str | None = None
    reveal_content: dict[str, Any] | None = None


@dataclass
class LabDefinition:
    id: str
    concept_node_id: str
    title: str
    required_shims: list[ShimId]
    visualizer_primitives: list[VisualizerPrimitiveType]
    beats: dict[int, LabBeatSpec]
    unit_tests: list[UnitTestSpec]

    def get_public_beat_payload(self, beat: LabBeatNumber) -> dict[str, Any]:
        """Return Beat metadata while strictly masking Beat 5 textbook jargon in Beats 1-4."""
        spec = self.beats[beat]
        payload: dict[str, Any] = {
            "lab_id": self.id,
            "concept_node_id": self.concept_node_id,
            "beat": spec.beat,
            "title": spec.title,
            "narrative": spec.narrative,
            "instructions": spec.instructions,
            "required_shims": list(self.required_shims),
            "visualizer_primitives": list(self.visualizer_primitives),
        }
        if spec.starter_code is not None:
            payload["starter_code"] = spec.starter_code
        if spec.diagnosis is not None:
            # Never expose `is_correct` before learner submits a diagnosis choice.
            payload["diagnosis"] = {
                "question": spec.diagnosis.question,
                "options": [{"id": o.id, "label": o.label} for o in spec.diagnosis.options],
            }
        if spec.stress_scenario_id is not None:
            payload["stress_scenario_id"] = spec.stress_scenario_id
        if beat == 5 and spec.reveal_content is not None:
            payload["reveal_content"] = spec.reveal_content
        return payload


@dataclass
class UnitTestResult:
    test_id: str
    name: str
    passed: bool
    message: str
    socratic_hint: str | None = None


@dataclass
class VisualizerMetric:
    label: str
    value: str | int | float
    status: Literal["healthy", "warning", "critical"]


@dataclass
class PrimitiveTracePayload:
    primitive: VisualizerPrimitiveType
    data: dict[str, Any]


@dataclass
class SimulationTrace:
    scenario_name: str
    failed_as_expected_in_beat2: bool = False
    passed_stress_in_beat4: bool = False
    headline_alert: dict[str, str] | None = None
    metrics: list[VisualizerMetric] = field(default_factory=list)
    primitive_payloads: list[PrimitiveTracePayload] = field(default_factory=list)


@dataclass
class ChallengeExecutionResult:
    lab_id: str
    beat: LabBeatNumber
    mode: Literal["unit_tests", "stress_simulation"]
    compile_error: str | None = None
    runtime_error: str | None = None
    timed_out: bool = False
    execution_ms: float = 0.0
    unit_test_results: list[UnitTestResult] = field(default_factory=list)
    all_tests_passed: bool = False
    simulation_trace: SimulationTrace | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
