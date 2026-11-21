"""Data schemas for Stage 3 Socratic Recall & Diagnostic Agent."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class SocraticRequest:
    concept_id: str
    question: str
    answer: str
    core_points: list[str] = field(default_factory=list)
    invariant_points: list[str] = field(default_factory=list)
    tradeoff_points: list[str] = field(default_factory=list)
    user_id: str = "default"


@dataclass
class RubricScores:
    core_principle_score: float       # 40% weight
    invariant_edge_case_score: float  # 30% weight
    tradeoff_score: float             # 30% weight
    weighted_total: float

    def to_dict(self) -> dict[str, float]:
        return asdict(self)


@dataclass
class DetectedMisconception:
    fallacy_category: str
    diagnostic_summary: str
    triggering_pattern: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass
class SocraticEvaluation:
    concept_id: str
    rubric: RubricScores
    covered_core: list[bool]
    covered_invariants: list[bool]
    covered_tradeoffs: list[bool]
    misconceptions: list[DetectedMisconception]
    follow_up_question: str | None
    feedback: str
    grader_source: str
    resolved_prior_misconceptions: int = 0

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        return data
