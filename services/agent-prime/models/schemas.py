"""Data schemas for Stage 1 Prime Agent."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class PrimeRequest:
    chapter_title: str
    chapter_text: str
    concept_id: str | None = None


@dataclass
class DialogueLine:
    speaker: str
    role: str
    text: str


@dataclass
class PrimeBriefing:
    chapter_title: str
    core_problem_statement: str
    dialogue: list[DialogueLine] = field(default_factory=list)
    key_invariants: list[str] = field(default_factory=list)
    schema_teaser: list[dict[str, str]] = field(default_factory=list)
    kv_cache_key: str = ""
    generation_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
