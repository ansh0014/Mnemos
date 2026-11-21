"""Zero-dependency BM25 + Character N-Gram Cosine Grounding Index.

Indexes book passages and curriculum documents so agents can ground answers via
``query_book_ground_truth(query, top_k=3)`` without external embedding binaries.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from typing import Any

_WORD_RE = re.compile(r"[a-z0-9_]+")


def _words(text: str) -> list[str]:
    return _WORD_RE.findall(text.lower())


def _trigrams(text: str) -> Counter[str]:
    clean = " ".join(_words(text))
    if len(clean) < 3:
        return Counter([clean]) if clean else Counter()
    return Counter(clean[i : i + 3] for i in range(len(clean) - 2))


def _cosine(a: Counter[str], b: Counter[str]) -> float:
    if not a or not b:
        return 0.0
    dot = sum(a[k] * b[k] for k in set(a) & set(b))
    norm_a = math.sqrt(sum(v * v for v in a.values()))
    norm_b = math.sqrt(sum(v * v for v in b.values()))
    return dot / (norm_a * norm_b) if norm_a and norm_b else 0.0


class LocalVectorIndex:
    """Hybrid BM25 + trigram cosine search index over book chunks."""

    def __init__(self) -> None:
        self._docs: list[dict[str, Any]] = []
        self._doc_words: list[Counter[str]] = []
        self._doc_trigrams: list[Counter[str]] = []
        self._df: Counter[str] = Counter()
        self._avg_len: float = 1.0

    def add_documents(self, docs: list[dict[str, Any]]) -> None:
        """Index documents with fields ``id``, ``text``, and optional metadata."""
        for doc in docs:
            text = str(doc.get("text", "")).strip()
            if not text:
                continue
            words = _words(text)
            tf = Counter(words)
            self._docs.append(doc)
            self._doc_words.append(tf)
            self._doc_trigrams.append(_trigrams(text))
            for term in tf:
                self._df[term] += 1
        total_len = sum(sum(c.values()) for c in self._doc_words)
        self._avg_len = total_len / len(self._docs) if self._docs else 1.0

    def query_book_ground_truth(self, query: str, top_k: int = 3) -> list[dict[str, Any]]:
        """Return top-k grounded passages ranked by hybrid BM25 + cosine trigram score."""
        if not self._docs or not query.strip():
            return []
        q_words = _words(query)
        q_trigrams = _trigrams(query)
        n_docs = len(self._docs)
        k1, b = 1.5, 0.75

        scored: list[tuple[float, dict[str, Any]]] = []
        for idx, doc in enumerate(self._docs):
            tf_map = self._doc_words[idx]
            doc_len = max(1, sum(tf_map.values()))
            bm25 = 0.0
            for term in q_words:
                df = self._df.get(term, 0)
                if df == 0:
                    continue
                idf = math.log(1.0 + (n_docs - df + 0.5) / (df + 0.5))
                tf = tf_map.get(term, 0)
                bm25 += idf * ((tf * (k1 + 1.0)) / (tf + k1 * (1.0 - b + b * (doc_len / self._avg_len))))

            tri_sim = _cosine(q_trigrams, self._doc_trigrams[idx])
            hybrid = round(0.65 * bm25 + 3.5 * tri_sim, 4)
            if hybrid > 0:
                scored.append((hybrid, doc))

        scored.sort(key=lambda item: item[0], reverse=True)
        return [{"score": s, **d} for s, d in scored[:top_k]]
