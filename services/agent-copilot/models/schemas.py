"""Data contracts for Stage 2 Conversational Active Reading Co-Pilot."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class CoPilotContext:
    section_text: str
    concept_id: str | None = None
    user_id: str = "default"
    language: str = "python"


@dataclass
class CodeSynthesisResult:
    language: str
    title: str
    code: str
    walkthrough: list[str] = field(default_factory=list)
    personalized_note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class WarStoryResult:
    concept: str
    company_or_system: str
    incident_summary: str
    root_cause: str
    engineering_lesson: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class DevilAdvocateResult:
    claim_examined: str
    sacrificed_properties: list[str] = field(default_factory=list)
    failure_modes_under_fault: list[str] = field(default_factory=list)
    when_not_to_use: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class SocraticMarginNote:
    anchor_quote: str
    margin_question: str
    hint: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
