"""Stage 2 Active Reading Co-Pilot Handler ('Show Me in Code', 'Reality Check', Margin Notes)."""

from __future__ import annotations

import re
from typing import Any

from mnemos_services.common import bootstrap_services
from mnemos_services.memory_engine.episodic.store import CognitiveMemoryStore
from mnemos_services.memory_engine.semantic.graph_memory import SemanticGraphMemory

bootstrap_services()

from neuralloop_books import convert  # noqa: E402

from ..models.schemas import (
    CodeSynthesisResult,
    DevilAdvocateResult,
    SocraticMarginNote,
    WarStoryResult,
)
from ..prompts.templates import (
    DEVILS_ADVOCATE_PROMPT,
    SHOW_ME_IN_CODE,
    WAR_STORY_PROMPT,
    build_copilot_prompt,
)

_CODE_CATALOG: dict[str, dict[str, dict[str, Any]]] = {
    "rate_limit": {
        "python": {
            "title": "Minimal Token Bucket Limiter (16 lines)",
            "code": (
                "class TokenBucket:\n"
                "    def __init__(self, cap: float, refill_per_sec: float, clock):\n"
                "        self.cap, self.rate, self.clock = cap, refill_per_sec, clock\n"
                "        self.buckets: dict[str, tuple[float, float]] = {}\n\n"
                "    def allow(self, client_id: str) -> bool:\n"
                "        now = self.clock.now() / 1000.0\n"
                "        tokens, last = self.buckets.get(client_id, (self.cap, now))\n"
                "        tokens = min(self.cap, tokens + max(0.0, now - last) * self.rate)\n"
                "        if tokens < 1.0:\n"
                "            self.buckets[client_id] = (tokens, now)\n"
                "            return False\n"
                "        self.buckets[client_id] = (tokens - 1.0, now)\n"
                "        return True"
            ),
            "walkthrough": [
                "Tracks continuous token refill based on elapsed time rather than resetting at :00.",
                "Caps accumulated tokens at burst capacity `cap` so idle clients cannot hoard infinite burst.",
            ],
        },
        "typescript": {
            "title": "Minimal Token Bucket Limiter (TypeScript)",
            "code": (
                "class TokenBucket {\n"
                "  private state = new Map<string, { tokens: number; lastMs: number }>();\n"
                "  constructor(private cap: number, private perSec: number, private clock: { now(): number }) {}\n"
                "  allow(id: string): boolean {\n"
                "    const now = this.clock.now();\n"
                "    const cur = this.state.get(id) ?? { tokens: this.cap, lastMs: now };\n"
                "    const refilled = Math.min(this.cap, cur.tokens + ((now - cur.lastMs) / 1000) * this.perSec);\n"
                "    if (refilled < 1) { this.state.set(id, { tokens: refilled, lastMs: now }); return false; }\n"
                "    this.state.set(id, { tokens: refilled - 1, lastMs: now });\n"
                "    return true;\n"
                "  }\n"
                "}"
            ),
            "walkthrough": ["Drips fractional tokens smoothly between requests without boundary spikes."],
        },
        "go": {
            "title": "Minimal Token Bucket Limiter (Go)",
            "code": (
                "type Bucket struct { Tokens, Cap, Rate float64; LastSec float64 }\n"
                "func (b *Bucket) Allow(nowSec float64) bool {\n"
                "    b.Tokens = min(b.Cap, b.Tokens + (nowSec - b.LastSec)*b.Rate)\n"
                "    b.LastSec = nowSec\n"
                "    if b.Tokens < 1 { return false }\n"
                "    b.Tokens -= 1\n"
                "    return true\n"
                "}"
            ),
            "walkthrough": ["Continuous timestamp delta eliminates fixed-window edge doubling."],
        },
    },
    "storage_index": {
        "python": {
            "title": "Hash-Indexed Append Log + Compaction (18 lines)",
            "code": (
                "class HashIndexedLog:\n"
                "    def __init__(self):\n"
                "        self.log: list[tuple[str, str]] = []\n"
                "        self.index: dict[str, int] = {}\n\n"
                "    def put(self, key: str, value: str) -> None:\n"
                "        self.index[key] = len(self.log)\n"
                "        self.log.append((key, value))\n\n"
                "    def get(self, key: str) -> str | None:\n"
                "        offset = self.index.get(key)\n"
                "        return None if offset is None else self.log[offset][1]\n\n"
                "    def compact(self) -> None:\n"
                "        live = [(k, self.log[pos][1]) for k, pos in self.index.items()]\n"
                "        self.log = live\n"
                "        self.index = {k: i for i, (k, _) in enumerate(self.log)}"
            ),
            "walkthrough": [
                "Writes remain sequential appends while `index` turns O(N) scans into O(1) offset jumps.",
                "`compact()` drops overwritten versions and rebuilds byte/record offsets atomically.",
            ],
        },
    },
    "consistent_hash": {
        "python": {
            "title": "Consistent Hash Ring with Virtual Nodes (18 lines)",
            "code": (
                "import bisect, zlib\n\n"
                "class HashRing:\n"
                "    def __init__(self, nodes: list[str], vnodes: int = 20):\n"
                "        self.ring: list[tuple[int, str]] = []\n"
                "        self.vnodes = vnodes\n"
                "        for n in nodes: self.add_node(n)\n\n"
                "    def _h(self, s: str) -> int: return zlib.crc32(s.encode())\n\n"
                "    def add_node(self, node: str) -> None:\n"
                "        for i in range(self.vnodes):\n"
                "            bisect.insort(self.ring, (self._h(f'{node}#{i}'), node))\n\n"
                "    def route(self, key: str) -> str | None:\n"
                "        if not self.ring: return None\n"
                "        idx = bisect.bisect_left(self.ring, (self._h(key), ''))\n"
                "        return self.ring[idx % len(self.ring)][1]"
            ),
            "walkthrough": [
                "Binary searches clockwise around a fixed 32-bit ring rather than taking `% len(nodes)`.",
                "Virtual nodes (`node#i`) spread load smoothly so losing 1 node moves ~1/N keys.",
            ],
        },
    },
    "idempotency": {
        "python": {
            "title": "Idempotent Webhook Consumer with Retry Safety (16 lines)",
            "code": (
                "class IdempotentWebhookProcessor:\n"
                "    def __init__(self):\n"
                "        self.seen: dict[str, dict] = {}\n"
                "        self.ledger: list[dict] = []\n\n"
                "    def handle(self, event_id: str, amount: int) -> dict:\n"
                "        if event_id in self.seen:\n"
                "            return {'status': 'duplicate_ignored', 'receipt': self.seen[event_id]}\n"
                "        receipt = {'event_id': event_id, 'charged': amount}\n"
                "        self.ledger.append(receipt)\n"
                "        self.seen[event_id] = receipt\n"
                "        return {'status': 'processed', 'receipt': receipt}"
            ),
            "walkthrough": [
                "Stores the deterministic outcome keyed by `Idempotency-Key` before returning 200 OK.",
                "Retried deliveries replay the saved receipt without re-charging the customer.",
            ],
        },
    },
}

_WAR_STORIES: list[tuple[tuple[str, ...], WarStoryResult]] = [
    (
        ("rate", "limit", "429", "burst", "token bucket", "window"),
        WarStoryResult(
            concept="Rate Limiting & Boundary Bursts",
            company_or_system="Stripe / Envoy API Gateways",
            incident_summary="Fixed-window counters allowed 2x traffic bursts across minute edges during flash sales.",
            root_cause="Quota counters reset synchronously at `:00`, letting callers stack end-of-window and start-of-window calls.",
            engineering_lesson="Use continuous token refill or sliding-window logs paired with jittered backoff.",
        ),
    ),
    (
        ("log", "index", "sstable", "lsm", "compaction", "bitcask", "disk"),
        WarStoryResult(
            concept="Log-Structured Storage & Compaction",
            company_or_system="RocksDB / Riak Bitcask / Kafka",
            incident_summary="High write-churn workloads suffered read p99 spikes and disk exhaustion before compaction tuned.",
            root_cause="Uncompacted append segments accumulate stale tombstones and force multi-file read amplification.",
            engineering_lesson="Index key offsets in memory (or sparse SSTable indexes + Bloom filters) and schedule background compaction.",
        ),
    ),
    (
        ("hash", "partition", "shard", "stampede", "consistent", "node"),
        WarStoryResult(
            concept="Modulo Resizing & Cache Stampedes",
            company_or_system="Amazon Dynamo / Discord / Memcached Clusters",
            incident_summary="Removing a single cache node under `hash(key) % N` invalidated >75% of cached entries at once.",
            root_cause="Changing divisor N shifts the remainder for almost every key, slamming the backing database simultaneously.",
            engineering_lesson="Use consistent hashing with virtual nodes so single-node loss only migrates ~1/N keys.",
        ),
    ),
    (
        ("webhook", "retry", "idempoten", "duplicate", "timeout", "payment"),
        WarStoryResult(
            concept="Duplicate Execution Under Network Retries",
            company_or_system="Stripe Webhooks & Payment Gateways",
            incident_summary="Transient 504 timeouts caused upstream webhook senders to retry already-committed payments.",
            root_cause="At-least-once network delivery without an Idempotency-Key deduplication store processed the event twice.",
            engineering_lesson="Enforce atomic idempotency keys on every non-idempotent state mutation.",
        ),
    ),
]


def _classify_topic(text: str) -> str:
    low = text.lower()
    if any(k in low for k in ("rate limit", "token bucket", "429", "burst", "fixed window")):
        return "rate_limit"
    if any(k in low for k in ("append", "compaction", "sstable", "lsm", "bitcask", "offset", "disk")):
        return "storage_index"
    if any(k in low for k in ("consistent hash", "modulo", "virtual node", "shard", "stampede")):
        return "consistent_hash"
    if any(k in low for k in ("webhook", "idempoten", "retry", "duplicate")):
        return "idempotency"
    return "rate_limit"


class CoPilotHandler:
    """In-situ reading co-pilot combining semantic graph + episodic learner history."""

    def __init__(
        self,
        semantic_memory: SemanticGraphMemory | None = None,
        episodic_memory: CognitiveMemoryStore | None = None,
        model: Any = None,
    ) -> None:
        self.semantic_memory = semantic_memory or SemanticGraphMemory()
        self.episodic_memory = episodic_memory
        self.model = model

    def get_active_section_text(
        self,
        section_text: str,
        concept_id: str | None = None,
        user_id: str = "default",
    ) -> dict[str, Any]:
        prereqs = self.semantic_memory.get_prerequisites(concept_id) if concept_id else []
        recent_failures = (
            self.episodic_memory.get_recent_failures(user_id=user_id, concept_id=concept_id, limit=3)
            if self.episodic_memory
            else []
        )
        return {
            "section_text": section_text,
            "word_count": len(section_text.split()),
            "prerequisites": [{"id": p["id"], "title": p["title"]} for p in prereqs],
            "recent_failures": recent_failures,
        }

    def lookup_prerequisite_term(self, term: str) -> dict[str, Any]:
        """Bridge in-situ unknown terms directly to the Grand Scheme Concept Compass."""
        return self.semantic_memory.where_does_this_fit(term)

    async def generate_code_example(
        self,
        paragraph: str,
        language: str = "python",
        concept_id: str | None = None,
        user_id: str = "default",
    ) -> dict[str, Any]:
        lang = language.lower()
        memory_note = ""
        if self.episodic_memory:
            failures = self.episodic_memory.get_recent_failures(user_id=user_id, concept_id=concept_id, limit=2)
            if failures:
                memory_note = f"Addresses past observed failure: {failures[0]['failure_mode_observed']}"

        if self.model is not None:
            try:
                bundle = build_copilot_prompt(
                    paragraph,
                    SHOW_ME_IN_CODE.format(language=lang, memory_notes=memory_note or "none"),
                )
                reply = await self.model.complete("copilot_code", bundle["system"], bundle["source"], bundle["prompt"])
                parsed = convert.loose_json(reply)
                if isinstance(parsed, dict) and parsed.get("code"):
                    return CodeSynthesisResult(
                        language=lang,
                        title=str(parsed.get("title", "Runnable Implementation")),
                        code=str(parsed["code"]),
                        walkthrough=[str(x) for x in parsed.get("walkthrough", [])],
                        personalized_note=memory_note,
                    ).to_dict()
            except Exception:
                pass

        topic = _classify_topic(f"{concept_id or ''} {paragraph}")
        lang_map = _CODE_CATALOG.get(topic, _CODE_CATALOG["rate_limit"])
        chosen = lang_map.get(lang) or lang_map["python"]
        actual_lang = lang if lang in lang_map else "python"
        return CodeSynthesisResult(
            language=actual_lang,
            title=chosen["title"],
            code=chosen["code"],
            walkthrough=list(chosen["walkthrough"]),
            personalized_note=memory_note,
        ).to_dict()

    async def get_production_war_story(self, concept_or_paragraph: str) -> dict[str, Any]:
        if self.model is not None:
            try:
                bundle = build_copilot_prompt(concept_or_paragraph, WAR_STORY_PROMPT)
                reply = await self.model.complete("copilot_war_story", bundle["system"], bundle["source"], bundle["prompt"])
                parsed = convert.loose_json(reply)
                if isinstance(parsed, dict) and parsed.get("incident_summary"):
                    return WarStoryResult(
                        concept=str(parsed.get("concept", "Systems Engineering")),
                        company_or_system=str(parsed.get("company_or_system", "Production System")),
                        incident_summary=str(parsed["incident_summary"]),
                        root_cause=str(parsed.get("root_cause", "")),
                        engineering_lesson=str(parsed.get("engineering_lesson", "")),
                    ).to_dict()
            except Exception:
                pass

        low = concept_or_paragraph.lower()
        for keywords, story in _WAR_STORIES:
            if any(kw in low for kw in keywords):
                return story.to_dict()
        return _WAR_STORIES[0][1].to_dict()

    async def devils_advocate_tradeoffs(
        self,
        paragraph: str,
        concept_id: str | None = None,
    ) -> dict[str, Any]:
        if self.model is not None:
            try:
                bundle = build_copilot_prompt(paragraph, DEVILS_ADVOCATE_PROMPT)
                reply = await self.model.complete("copilot_devil", bundle["system"], bundle["source"], bundle["prompt"])
                parsed = convert.loose_json(reply)
                if isinstance(parsed, dict) and parsed.get("sacrificed_properties"):
                    return DevilAdvocateResult(
                        claim_examined=str(parsed.get("claim_examined", "")),
                        sacrificed_properties=[str(x) for x in parsed.get("sacrificed_properties", [])],
                        failure_modes_under_fault=[str(x) for x in parsed.get("failure_modes_under_fault", [])],
                        when_not_to_use=str(parsed.get("when_not_to_use", "")),
                    ).to_dict()
            except Exception:
                pass

        node = self.semantic_memory.get_node(concept_id) if concept_id else None
        tradeoffs = node.get("tradeoffs", []) if node else []
        first_sentence = re.split(r"(?<=[.!?])\s+", paragraph.strip())[0][:160]
        return DevilAdvocateResult(
            claim_examined=first_sentence,
            sacrificed_properties=tradeoffs or [
                "Added memory metadata or operational complexity in exchange for predictable tail latency."
            ],
            failure_modes_under_fault=[
                "Clock skew or garbage-collection pauses can distort timing assumptions.",
                "Partial failures and unbounded retries amplify load if idempotency or backpressure is missing.",
            ],
            when_not_to_use="Avoid premature distributed complexity when single-node throughput comfortably fits SLA.",
        ).to_dict()

    def generate_margin_notes(self, section_text: str, max_notes: int = 2) -> list[dict[str, Any]]:
        """Emit concise 1-sentence Socratic margin questions anchored to dense sentences."""
        sentences = [
            s.strip()
            for s in re.split(r"(?<=[.!?])\s+", section_text.strip())
            if len(s.strip()) > 35
        ]
        notes: list[SocraticMarginNote] = []
        for sentence in sentences[:max_notes]:
            low = sentence.lower()
            if "window" in low or "minute" in low or "rate" in low:
                q = "What happens if 10 requests arrive at 00:59 and 10 more arrive at 01:01?"
                hint = "Notice whether quota resets all at once or drips smoothly."
            elif "append" in low or "log" in low or "disk" in low:
                q = "If writes only append sequentially, how many records must a read inspect after 10,000 updates?"
                hint = "Think about what metadata in RAM could skip scanning old records."
            elif "hash" in low or "node" in low or "shard" in low:
                q = "If one server crashes and N drops from 4 to 3, how many keys change `hash(key) % N`?"
                hint = "Check whether unaffected healthy servers lose their cached keys."
            else:
                q = "Which single assumption in this sentence breaks first under sudden load or a partial crash?"
                hint = "Trace what state lives in volatile memory vs. shared across nodes."
            notes.append(SocraticMarginNote(anchor_quote=sentence[:120], margin_question=q, hint=hint))
        return [n.to_dict() for n in notes]
