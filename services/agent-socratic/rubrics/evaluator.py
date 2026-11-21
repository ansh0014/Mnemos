"""3-Tier Weighted Engineering Rubric & Misconception Anti-Pattern Classifier.

Extends ``neuralloop_books.recall`` (preserving grounded evidence checking and
multi-script fallback word matching) with ``left.md`` Task 5:
- Core Principle (40%)
- Invariant / Edge Case (30%)
- Trade-offs (30%)
- Misconception & Anti-Pattern detection + targeted Socratic follow-up probing.
"""

from __future__ import annotations

import re
from typing import Any

from mnemos_services.common import bootstrap_services

bootstrap_services()

from neuralloop_books import recall as nl_recall  # noqa: E402

from ..models.schemas import DetectedMisconception, RubricScores

# Weighted rubric constants from left.md Task 5.1
WEIGHT_CORE = 0.40
WEIGHT_INVARIANT = 0.30
WEIGHT_TRADEOFF = 0.30

_ANTI_PATTERNS: list[dict[str, Any]] = [
    {
        "category": "fixed_window_boundary_blindness",
        "concept_hints": ("rate", "limit", "window", "token"),
        "pattern": re.compile(r"(fixed\s+window|per[- ]minute\s+counter).*(prevent|stop|no).*(burst|spike)", re.I),
        "summary": "Assumes a per-minute counter blocks boundary bursts; 2x requests can still pass at :59 and :01.",
        "probe": "If 10 requests arrive at 00:59 and 10 more at 01:01, how many requests hit your database in 2 seconds?",
    },
    {
        "category": "modulo_resizing_blindness",
        "concept_hints": ("hash", "shard", "partition", "consistent"),
        "pattern": re.compile(r"(modulo|%\s*n).*(only|few|minimal).*(move|migrate|rebalanc)", re.I),
        "summary": "Assumes `hash(key) % N` only moves keys from the dead node; changing N scrambles ~75%+ of remainders.",
        "probe": "When N changes from 4 to 3, what happens to `hash('user:1') % N` even on the 3 surviving servers?",
    },
    {
        "category": "unindexed_append_log_read_myth",
        "concept_hints": ("storage", "log", "index", "bitcask", "lsm"),
        "pattern": re.compile(r"(append[- ]only|log).*(always\s+fast|o\(1\))\s+(read|get|lookup)", re.I),
        "summary": "Conflates O(1) sequential append writes with O(N) backward log scans during reads.",
        "probe": "Writing to the end of a file is O(1), so without an in-memory map of offsets, how does `get(key)` find the newest value?",
    },
    {
        "category": "retry_without_idempotency",
        "concept_hints": ("webhook", "retry", "idempoten", "payment"),
        "pattern": re.compile(r"(retry|backoff).*(safe|never\s+duplicate|exactly[- ]once)", re.I),
        "summary": "Assumes retries alone guarantee once-only execution; lost ACKs trigger duplicate execution without idempotency keys.",
        "probe": "If the server actually charged the card and then the 200 OK response timed out on the network, what happens when the sender retries?",
    },
    {
        "category": "linearizability_vs_serializability",
        "concept_hints": ("consisten", "lineariz", "serializ", "isolation", "paxos"),
        "pattern": re.compile(r"(linearizab|serializab).*(same\s+thing|identical|means\s+transaction)", re.I),
        "summary": "Conflates linearizability (single-object recency guarantee) with serializability (multi-object transaction isolation).",
        "probe": "Does linearizability protect multi-row transactions across tables, or is it a recency guarantee on one register?",
    },
]


def classify_misconceptions(concept_id: str, answer: str) -> list[DetectedMisconception]:
    """Detect domain anti-patterns and conceptual fallacies in a free-text explanation."""
    found: list[DetectedMisconception] = []
    cid_low = concept_id.lower()
    for rule in _ANTI_PATTERNS:
        if rule["concept_hints"] and not any(h in cid_low or h in answer.lower() for h in rule["concept_hints"]):
            continue
        match = rule["pattern"].search(answer)
        if match:
            found.append(
                DetectedMisconception(
                    fallacy_category=rule["category"],
                    diagnostic_summary=rule["summary"],
                    triggering_pattern=match.group(0),
                )
            )
    return found


def build_targeted_probe(
    misconceptions: list[DetectedMisconception],
    missing_core: list[str],
    missing_invariants: list[str],
    missing_tradeoffs: list[str],
    weighted_total: float,
) -> str | None:
    """Return ONE targeted Socratic probing question when score is partial or a misconception fires."""
    if misconceptions:
        first_cat = misconceptions[0].fallacy_category
        for rule in _ANTI_PATTERNS:
            if rule["category"] == first_cat:
                return str(rule["probe"])

    if weighted_total >= 0.85:
        return None
    if missing_core:
        return f"Walk me through the core mechanism: what problem forces {missing_core[0]}?"
    if missing_invariants:
        return f"What boundary condition or failure breaks the naive version if {missing_invariants[0]} isn't handled?"
    if missing_tradeoffs:
        return f"What cost or downside do you pay when choosing this design around {missing_tradeoffs[0]}?"
    return None


async def grade_rubric(
    model: Any,
    question: str,
    answer: str,
    core_points: list[str],
    invariant_points: list[str],
    tradeoff_points: list[str],
) -> tuple[RubricScores, list[bool], list[bool], list[bool], str]:
    """Evaluate all three rubric tiers using ``neuralloop_books.recall.grade``."""
    all_points = [*core_points, *invariant_points, *tradeoff_points]
    if not all_points or not answer.strip():
        empty_scores = RubricScores(0.0, 0.0, 0.0, 0.0)
        return (
            empty_scores,
            [False] * len(core_points),
            [False] * len(invariant_points),
            [False] * len(tradeoff_points),
            "empty" if not answer.strip() else "none",
        )

    if model is not None:
        res = await nl_recall.grade(model, question, all_points, answer)
        covered = res["covered"]
        grader = str(res["by"])
    else:
        covered = nl_recall.word_match(all_points, answer)
        grader = "word match"

    c_len = len(core_points)
    i_len = len(invariant_points)
    cov_core = covered[:c_len]
    cov_inv = covered[c_len : c_len + i_len]
    cov_trade = covered[c_len + i_len :]

    core_score = (sum(cov_core) / len(cov_core)) if cov_core else 1.0
    inv_score = (sum(cov_inv) / len(cov_inv)) if cov_inv else 1.0
    trade_score = (sum(cov_trade) / len(cov_trade)) if cov_trade else 1.0

    # Normalize weights across whichever tiers were supplied.
    active_weights = (
        (WEIGHT_CORE if core_points else 0.0)
        + (WEIGHT_INVARIANT if invariant_points else 0.0)
        + (WEIGHT_TRADEOFF if tradeoff_points else 0.0)
    )
    raw_weighted = (
        (core_score * WEIGHT_CORE if core_points else 0.0)
        + (inv_score * WEIGHT_INVARIANT if invariant_points else 0.0)
        + (trade_score * WEIGHT_TRADEOFF if tradeoff_points else 0.0)
    )
    weighted_total = round(raw_weighted / active_weights, 4) if active_weights else 0.0

    return (
        RubricScores(
            core_principle_score=round(core_score, 4),
            invariant_edge_case_score=round(inv_score, 4),
            tradeoff_score=round(trade_score, 4),
            weighted_total=weighted_total,
        ),
        cov_core,
        cov_inv,
        cov_trade,
        grader,
    )
