"""Semantic Knowledge Graph Memory & 'Where Does This Fit?' Concept Compass.

Provides graph traversal (``get_prerequisites``, ``get_downstream_dependents``,
``find_missing_links``) and bottom-up buzzword resolution (``where_does_this_fit``)
over the Knowledge Graph built by ``ingestion-engine``.
"""

from __future__ import annotations

import re
from typing import Any

from mnemos_services.ingestion_engine.graph.knowledge_graph import get_active_curriculum


def _tokenize(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]{3,}", text.lower())}


class SemanticGraphMemory:
    """In-memory semantic query layer over the Grand Scheme Knowledge Graph."""

    def __init__(self, curriculum: dict[str, Any] | None = None) -> None:
        self.curriculum = curriculum or get_active_curriculum()
        self._nodes: dict[str, dict[str, Any]] = {n["id"]: n for n in self.curriculum.get("nodes", [])}
        self._edges: list[dict[str, Any]] = list(self.curriculum.get("edges", []))

    def get_node(self, concept_id: str) -> dict[str, Any] | None:
        return self._nodes.get(concept_id)

    def get_prerequisites(self, concept_id: str) -> list[dict[str, Any]]:
        """Return upstream concepts that motivate or feed into ``concept_id``."""
        prereq_ids = [
            e["source"]
            for e in self._edges
            if e["target"] == concept_id and e.get("relation", e.get("type")) in {"prerequisite", "evolves_into", "depends_on", "builds_on"}
        ]
        # Also honor edges written in depends_on direction (source depends on target)
        prereq_ids.extend(
            e["target"]
            for e in self._edges
            if e["source"] == concept_id and e.get("relation", e.get("type")) in {"depends_on", "builds_on"}
        )
        seen: set[str] = set()
        results: list[dict[str, Any]] = []
        for pid in prereq_ids:
            if pid not in seen and pid in self._nodes:
                seen.add(pid)
                results.append(self._nodes[pid])
        return results

    def get_downstream_dependents(self, concept_id: str) -> list[dict[str, Any]]:
        """Return concepts unlocked or motivated downstream of ``concept_id``."""
        down_ids = [e["target"] for e in self._edges if e["source"] == concept_id]
        return [self._nodes[did] for did in dict.fromkeys(down_ids) if did in self._nodes]

    def get_sibling_tradeoffs(self, concept_id: str) -> list[dict[str, Any]]:
        """Return alternative concepts connected by ``tradeoff`` edges or same domain."""
        tradeoff_ids = [
            e["target"] if e["source"] == concept_id else e["source"]
            for e in self._edges
            if e.get("relation", e.get("type")) == "tradeoff" and concept_id in {e["source"], e["target"]}
        ]
        return [self._nodes[tid] for tid in dict.fromkeys(tradeoff_ids) if tid in self._nodes]

    def where_does_this_fit(self, query: str) -> dict[str, Any]:
        """Concept Compass: map any googled term/alias to its place in the Grand Scheme."""
        needle = query.strip().lower()
        if not needle:
            return {"matches": []}

        scored: list[tuple[int, dict[str, Any], str]] = []
        for node in self._nodes.values():
            best_score = 0
            matched_via = ""
            title = str(node.get("title", "")).lower()
            intuition = str(node.get("intuition_title", "")).lower()

            if needle == title or needle in node["id"].lower():
                best_score, matched_via = 100, "exact_title"
            elif needle in title or needle in intuition:
                best_score, matched_via = 80, "title_substring"

            for alias in node.get("aliases", []):
                term = str(alias.get("term", "")).lower()
                if needle == term:
                    if 95 > best_score:
                        best_score, matched_via = 95, f"alias:{alias['term']}"
                elif needle in term or term in needle:
                    if 75 > best_score:
                        best_score, matched_via = 75, f"alias:{alias['term']}"

            if best_score == 0:
                q_tokens = _tokenize(needle)
                blob_tokens = _tokenize(
                    " ".join([title, intuition, str(node.get("summary", "")), str(node.get("why_it_exists", ""))])
                )
                overlap = len(q_tokens & blob_tokens)
                if overlap:
                    best_score = 40 + min(30, overlap * 15)
                    matched_via = "semantic_overlap"

            if best_score > 0:
                scored.append((best_score, node, matched_via))

        scored.sort(key=lambda item: item[0], reverse=True)
        matches = []
        for score, node, matched_via in scored[:5]:
            matches.append(
                {
                    "score": score,
                    "matched_via": matched_via,
                    "node": node,
                    "grand_scheme_path": {
                        "domain": node.get("domain", "general"),
                        "chapter": node.get("chapter"),
                        "book_refs": node.get("book_refs", []),
                    },
                    "upstream_prerequisites": [
                        {"id": p["id"], "title": p["title"], "why_it_exists": p.get("why_it_exists", "")}
                        for p in self.get_prerequisites(node["id"])
                    ],
                    "downstream_concepts": [
                        {"id": d["id"], "title": d["title"]} for d in self.get_downstream_dependents(node["id"])
                    ],
                    "sibling_tradeoffs": [
                        {"id": s["id"], "title": s["title"]} for s in self.get_sibling_tradeoffs(node["id"])
                    ],
                    "recommended_lab_id": node.get("lab_id"),
                }
            )
        return {"query": query, "matches": matches}

    def find_missing_links(self, concept_id: str, learner_explanation: str) -> list[dict[str, Any]]:
        """Identify prerequisite concepts not yet reflected in a learner's explanation."""
        said = _tokenize(learner_explanation)
        missing: list[dict[str, Any]] = []
        for prereq in self.get_prerequisites(concept_id):
            expected = _tokenize(f"{prereq.get('title', '')} {prereq.get('summary', '')}")
            if not (said & expected):
                missing.append({"id": prereq["id"], "title": prereq["title"], "summary": prereq.get("summary", "")})
        return missing
