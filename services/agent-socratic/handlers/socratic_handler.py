"""Stage 3 Socratic Diagnostic Handler integrated with Episodic & Vector Memory."""

from __future__ import annotations

from typing import Any

from mnemos_services.memory_engine.episodic.store import CognitiveMemoryStore
from mnemos_services.memory_engine.semantic.graph_memory import SemanticGraphMemory
from mnemos_services.memory_engine.vector.index import LocalVectorIndex

from ..models.schemas import SocraticEvaluation, SocraticRequest
from ..rubrics.evaluator import build_targeted_probe, classify_misconceptions, grade_rubric


class SocraticHandler:
    """Evaluates learner explanations, tracks misconceptions, and probes gaps gently."""

    def __init__(
        self,
        memory_store: CognitiveMemoryStore | None = None,
        semantic_memory: SemanticGraphMemory | None = None,
        vector_index: LocalVectorIndex | None = None,
        model: Any = None,
    ) -> None:
        self.memory_store = memory_store or CognitiveMemoryStore(":memory:")
        self.semantic_memory = semantic_memory or SemanticGraphMemory()
        self.vector_index = vector_index or self._build_default_index()
        self.model = model

    def _build_default_index(self) -> LocalVectorIndex:
        idx = LocalVectorIndex()
        docs = [
            {
                "id": node["id"],
                "title": node["title"],
                "text": f"{node['title']}. {node['summary']} {node['why_it_exists']} {' '.join(node.get('tradeoffs', []))}",
            }
            for node in self.semantic_memory.curriculum.get("nodes", [])
        ]
        idx.add_documents(docs)
        return idx

    def query_book_ground_truth(self, query: str, top_k: int = 3) -> dict[str, Any]:
        return {"query": query, "results": self.vector_index.query_book_ground_truth(query, top_k=top_k)}

    def get_learner_misconceptions(self, concept_id: str | None = None, user_id: str = "default") -> dict[str, Any]:
        return {
            "concept_id": concept_id,
            "misconceptions": self.memory_store.get_misconceptions(concept_id=concept_id, user_id=user_id),
        }

    def log_misconception_resolution(self, concept_id: str, user_id: str = "default") -> dict[str, Any]:
        resolved = self.memory_store.resolve_misconceptions(concept_id=concept_id, user_id=user_id)
        return {"concept_id": concept_id, "resolved_count": resolved}

    async def evaluate_socratic_recall(self, req: SocraticRequest) -> dict[str, Any]:
        rubric, cov_core, cov_inv, cov_trade, grader = await grade_rubric(
            self.model,
            req.question,
            req.answer,
            req.core_points,
            req.invariant_points,
            req.tradeoff_points,
        )
        misconceptions = classify_misconceptions(req.concept_id, req.answer)

        # Penalize weighted score gently when an explicit fallacy pattern is present.
        if misconceptions:
            rubric.weighted_total = round(max(0.0, rubric.weighted_total - 0.15 * len(misconceptions)), 4)

        missing_core = [p for p, ok in zip(req.core_points, cov_core, strict=True) if not ok]
        missing_inv = [p for p, ok in zip(req.invariant_points, cov_inv, strict=True) if not ok]
        missing_trade = [p for p, ok in zip(req.tradeoff_points, cov_trade, strict=True) if not ok]

        for misc in misconceptions:
            self.memory_store.record_misconception(
                concept_id=req.concept_id,
                fallacy_category=misc.fallacy_category,
                diagnostic_summary=misc.diagnostic_summary,
                triggering_pattern=misc.triggering_pattern,
                user_id=req.user_id,
            )
            self.memory_store.log_episodic_event(
                stage="socratic_recall",
                failure_mode_observed=misc.diagnostic_summary,
                user_id=req.user_id,
                concept_id=req.concept_id,
            )

        resolved_count = 0
        if not misconceptions and rubric.weighted_total >= 0.80:
            resolved_count = self.memory_store.resolve_misconceptions(req.concept_id, user_id=req.user_id)

        node = self.semantic_memory.get_node(req.concept_id)
        domain = node["domain"] if node else "systems"
        title = node["title"] if node else req.concept_id
        self.memory_store.update_concept_mastery(
            concept_id=req.concept_id,
            domain=domain,
            canonical_name=title,
            score=rubric.weighted_total,
            passed=(rubric.weighted_total >= 0.75 and not misconceptions),
        )

        probe = build_targeted_probe(
            misconceptions,
            missing_core,
            missing_inv,
            missing_trade,
            rubric.weighted_total,
        )

        if not misconceptions and rubric.weighted_total >= 0.85:
            feedback = "Strong explanation: you covered the core principle, failure invariants, and trade-offs."
        elif misconceptions:
            feedback = f"Good attempt—spot this subtle trap: {misconceptions[0].diagnostic_summary}"
        elif rubric.weighted_total >= 0.40:
            feedback = "You nailed part of the mechanism. Follow the probing question below to close the remaining gap."
        else:
            feedback = "Let's build it up step by step from the core failure case."

        evaluation = SocraticEvaluation(
            concept_id=req.concept_id,
            rubric=rubric,
            covered_core=cov_core,
            covered_invariants=cov_inv,
            covered_tradeoffs=cov_trade,
            misconceptions=misconceptions,
            follow_up_question=probe,
            feedback=feedback,
            grader_source=grader,
            resolved_prior_misconceptions=resolved_count,
        )
        return evaluation.to_dict()
