"""Stage 1 Prime Handler: sub-2s architectural problem framing & Theo/Ada dialogue."""

from __future__ import annotations

import re
import time
from typing import Any

from mnemos_services.common import bootstrap_services
from mnemos_services.memory_engine.semantic.graph_memory import SemanticGraphMemory

bootstrap_services()

from neuralloop_books import convert  # noqa: E402

from ..models.schemas import DialogueLine, PrimeBriefing, PrimeRequest
from ..prompts.templates import build_prime_prompt


def _extract_sentences(text: str, limit: int = 3) -> list[str]:
    clean = re.sub(r"[#`*_]+", " ", text)
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", clean) if len(s.strip()) > 25]
    return sentences[:limit]


class PrimeHandler:
    """Synthesizes Stage 1 Prime briefings in <2s, with optional LLM or instant offline synthesis."""

    def __init__(self, semantic_memory: SemanticGraphMemory | None = None, model: Any = None) -> None:
        self.semantic_memory = semantic_memory or SemanticGraphMemory()
        self.model = model

    async def generate_dialogue_briefing(self, req: PrimeRequest) -> dict[str, Any]:
        started = time.perf_counter()
        prompt_bundle = build_prime_prompt(req.chapter_title, req.chapter_text)
        node = self.semantic_memory.get_node(req.concept_id) if req.concept_id else None

        if self.model is not None:
            try:
                raw = await self.model.complete(
                    "prime",
                    prompt_bundle["system"],
                    prompt_bundle["source"],
                    prompt_bundle["prompt"],
                )
                parsed = convert.loose_json(raw)
                if isinstance(parsed, dict) and parsed.get("dialogue"):
                    briefing = PrimeBriefing(
                        chapter_title=req.chapter_title,
                        core_problem_statement=str(parsed.get("core_problem_statement", "")),
                        dialogue=[
                            DialogueLine(
                                speaker=str(d.get("speaker", "Ada")),
                                role=str(d.get("role", "Engineer")),
                                text=str(d.get("text", "")),
                            )
                            for d in parsed["dialogue"]
                        ],
                        key_invariants=[str(x) for x in parsed.get("key_invariants", [])],
                        schema_teaser=self._build_teaser(req.concept_id),
                        kv_cache_key=prompt_bundle["kv_cache_key"],
                        generation_ms=round((time.perf_counter() - started) * 1000.0, 2),
                    )
                    return briefing.to_dict()
            except Exception:
                pass  # Deterministic fallback guarantees <2s responsiveness even offline.

        sentences = _extract_sentences(req.chapter_text)
        problem = (
            node["why_it_exists"]
            if node and node.get("why_it_exists")
            else (sentences[0] if sentences else f"Understanding the core trade-off behind {req.chapter_title}.")
        )
        summary_point = (
            node["summary"]
            if node and node.get("summary")
            else (sentences[1] if len(sentences) > 1 else "Balance latency, durability, and blast radius.")
        )
        tradeoffs = node.get("tradeoffs", []) if node else ["Simple baseline fails under burst or failure pressure."]

        dialogue = [
            DialogueLine(
                speaker="Ada",
                role="Backend Engineer",
                text=f"When studying {req.chapter_title}, why can't we just ship the simplest naive solution?",
            ),
            DialogueLine(
                speaker="Theo",
                role="Staff Architect",
                text=f"Because in production: {problem}",
            ),
            DialogueLine(
                speaker="Ada",
                role="Backend Engineer",
                text="Got it — so what single invariant changes our architecture here?",
            ),
            DialogueLine(
                speaker="Theo",
                role="Staff Architect",
                text=f"{summary_point} Remember the real price you pay: {tradeoffs[0] if tradeoffs else 'memory vs. latency'}.",
            ),
        ]

        briefing = PrimeBriefing(
            chapter_title=req.chapter_title,
            core_problem_statement=problem,
            dialogue=dialogue,
            key_invariants=[summary_point, *(tradeoffs[:2])],
            schema_teaser=self._build_teaser(req.concept_id),
            kv_cache_key=prompt_bundle["kv_cache_key"],
            generation_ms=round((time.perf_counter() - started) * 1000.0, 2),
        )
        return briefing.to_dict()

    def get_chapter_summary(self, chapter_title: str, chapter_text: str) -> dict[str, Any]:
        sentences = _extract_sentences(chapter_text, limit=3)
        return {
            "chapter_title": chapter_title,
            "summary": " ".join(sentences) if sentences else f"Overview of {chapter_title}.",
            "word_count": len(chapter_text.split()),
        }

    def _build_teaser(self, concept_id: str | None) -> list[dict[str, str]]:
        if not concept_id:
            return []
        prereqs = self.semantic_memory.get_prerequisites(concept_id)
        downs = self.semantic_memory.get_downstream_dependents(concept_id)
        teaser = [{"relation": "prerequisite", "id": p["id"], "title": p["title"]} for p in prereqs]
        teaser.extend({"relation": "unlocks", "id": d["id"], "title": d["title"]} for d in downs)
        return teaser
