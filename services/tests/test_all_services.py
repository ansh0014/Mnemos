"""End-to-end automated verification tests for all 6 Mnemos Python services."""

from __future__ import annotations

import asyncio
import json
import sys
import threading
import time
import unittest
import urllib.request
from pathlib import Path

SERVICES_DIR = Path(__file__).resolve().parent.parent
if str(SERVICES_DIR) not in sys.path:
    sys.path.insert(0, str(SERVICES_DIR))

from common import bootstrap_services  # noqa: E402

bootstrap_services()

from mnemos_services.agent_challenge.scenarios.labs import LAB_DEFINITIONS  # noqa: E402
from mnemos_services.agent_challenge.scenarios.sandbox import execute_in_sandbox  # noqa: E402
from mnemos_services.agent_prime.models.schemas import PrimeRequest  # noqa: E402
from mnemos_services.agent_socratic.models.schemas import SocraticRequest  # noqa: E402
from mnemos_services.common.mcp_gateway import AgentRole, make_http_server  # noqa: E402
from mnemos_services.common.optimizer import (  # noqa: E402
    align_kv_cache_prefix,
    compact_conversation_history,
    project_response_fields,
)
from mnemos_services.common.runtime import create_integrated_runtime  # noqa: E402
from mnemos_services.ingestion_engine.parser.book_parser import (  # noqa: E402
    ingest_book_file,
    parse_markdown_book,
)
from neuralloop_books.models.fake import FakeModel  # noqa: E402

# ---------------------------------------------------------------------------
# Reference Beat 1 (Naive) and Beat 4 (Evolved) User Code for all 4 Labs
# ---------------------------------------------------------------------------

RATE_LIMITER_BEAT1 = LAB_DEFINITIONS["rate_limiter"].beats[1].starter_code or ""
RATE_LIMITER_BEAT4 = """class RequestGuard:
    def __init__(self, max_per_minute: int, clock):
        self.max_per_minute = float(max_per_minute)
        self.clock = clock
        self.state = {}

    def allow_request(self, client_id: str) -> bool:
        now = self.clock.now()
        tokens, last_ms = self.state.get(client_id, (self.max_per_minute, now))
        elapsed_ms = max(0, now - last_ms)
        tokens = min(self.max_per_minute, tokens + (elapsed_ms / 60000.0) * self.max_per_minute)
        if tokens < 1.0:
            self.state[client_id] = (tokens, now)
            return False
        self.state[client_id] = (tokens - 1.0, now)
        return True
"""

STORAGE_BEAT1 = LAB_DEFINITIONS["storage_engine"].beats[1].starter_code or ""
STORAGE_BEAT4 = """class MiniKVStore:
    def __init__(self, disk):
        self.disk = disk
        self.offsets = {}

    def set(self, key: str, value: str) -> None:
        self.offsets[key] = self.disk.append(key, value)

    def get(self, key: str):
        offset = self.offsets.get(key)
        if offset is None:
            return None
        rec = self.disk.read_at(offset)
        return rec["value"] if rec else None

    def compact(self) -> None:
        live = []
        for k, off in self.offsets.items():
            rec = self.disk.read_at(off)
            if rec is not None:
                live.append((k, rec["value"]))
        self.disk.rewrite_compacted(live)
        self.offsets = {}
        for entry in self.disk.scan_all():
            self.offsets[entry["key"]] = entry["offset"]
"""

HASH_BEAT1 = LAB_DEFINITIONS["consistent_hashing"].beats[1].starter_code or ""
HASH_BEAT4 = """import bisect

class ClusterRouter:
    def __init__(self, initial_nodes: list[str], helper):
        self.helper = helper
        self.vnodes = 25
        self.ring = []
        self.active = set()
        for n in initial_nodes:
            self.add_node(n)

    def add_node(self, node_id: str) -> None:
        if node_id in self.active:
            return
        self.active.add(node_id)
        for i in range(self.vnodes):
            pt = self.helper.hash(f"{node_id}#{i}")
            bisect.insort(self.ring, (pt, node_id))

    def remove_node(self, node_id: str) -> None:
        if node_id not in self.active:
            return
        self.active.remove(node_id)
        self.ring = [(pt, nid) for pt, nid in self.ring if nid != node_id]

    def route_key(self, key: str):
        if not self.ring:
            return None
        h = self.helper.hash(key)
        idx = bisect.bisect_left(self.ring, (h, ""))
        return self.ring[idx % len(self.ring)][1]
"""

WEBHOOK_BEAT1 = LAB_DEFINITIONS["webhook_idempotency"].beats[1].starter_code or ""
WEBHOOK_BEAT4 = """class PaymentWebhookConsumer:
    def __init__(self, ledger):
        self.ledger = ledger
        self.processed = {}

    def handle_delivery(self, event_id: str, amount_cents: int) -> dict:
        if event_id in self.processed:
            return {"status": "duplicate_ignored", "receipt": self.processed[event_id]}
        receipt = self.ledger.charge(event_id, amount_cents)
        self.processed[event_id] = receipt
        return {"status": "processed", "receipt": receipt}
"""


class TestMnemosPythonServices(unittest.TestCase):
    def setUp(self) -> None:
        self.runtime = create_integrated_runtime(db_path=":memory:")

    def tearDown(self) -> None:
        self.runtime.memory_store.close()

    # ------------------------------------------------------------------
    # Test 1: MCP Gateway & DeepMind Token Optimizer
    # ------------------------------------------------------------------
    def test_mcp_gateway_scoping_and_deepmind_optimizer(self) -> None:
        gw = self.runtime.gateway
        prime_scoped = gw.get_scoped_tools(AgentRole.PRIME, compact=True)
        prime_names = {t["name"] for t in prime_scoped["tools"]}
        self.assertIn("generate_dialogue_briefing", prime_names)
        self.assertNotIn("inject_simulation_fault", prime_names)
        self.assertGreater(prime_scoped["savings_pct"], 45.0)

        # Unauthorized access raises PermissionError
        with self.assertRaises(PermissionError):
            asyncio.run(
                gw.invoke_tool(
                    AgentRole.PRIME,
                    "inject_simulation_fault",
                    {"lab_id": "rate_limiter", "beat": 2, "user_code": RATE_LIMITER_BEAT1},
                )
            )

        # Response field projection filters payload down strictly
        projected = project_response_fields(
            {"title": "Hash Indexes", "raw_blob": "x" * 5000, "meta": {"chapter": 3, "noise": "y"}},
            ["title", "meta.chapter"],
        )
        self.assertEqual(projected, {"title": "Hash Indexes", "meta": {"chapter": 3}})

        # 4K KV cache prefix alignment
        kv = align_kv_cache_prefix("System instructions for active reader", block_tokens=4096)
        self.assertEqual(kv["aligned_tokens"], 4096)
        self.assertTrue(kv["kv_cache_key"].startswith("kv-4096-"))

        # Circuit breaker trips after 3 consecutive failures
        def _flaky_tool() -> dict:
            raise RuntimeError("downstream timeout")

        gw.register_tool(
            name="flaky_probe",
            description="Simulated flaky endpoint.",
            input_schema={"type": "object", "properties": {}},
            allowed_roles={AgentRole.PRIME},
            handler=_flaky_tool,
        )
        for _ in range(3):
            failed = asyncio.run(gw.invoke_tool(AgentRole.PRIME, "flaky_probe"))
            self.assertEqual(failed["status"], "failed")
        tripped = asyncio.run(gw.invoke_tool(AgentRole.PRIME, "flaky_probe"))
        self.assertEqual(tripped["status"], "circuit_open")

        # Sliding-window semantic history compaction
        turns = [
            {
                "role": "user" if i % 2 == 0 else "assistant",
                "content": (
                    f"Turn {i}: Detailed walkthrough of append-only segments, disk seeks, and offset maps.\n"
                    "When overwrites pile up, reading backward scans O(N) records on disk.\n"
                    f"```py\noffsets[key] = disk.append(key, val_{i})\n```\n"
                    "Compacting drops old overwrites while preserving live offsets safely."
                ),
            }
            for i in range(10)
        ]
        compacted = compact_conversation_history(turns, keep_recent=3)
        self.assertEqual(len(compacted["retained_turns"]), 3)
        self.assertIn("[contains code]", compacted["summary_delta"])
        self.assertGreater(compacted["savings_pct"], 30.0)

    # ------------------------------------------------------------------
    # Test 2: Ingestion Engine & Concept Compass
    # ------------------------------------------------------------------
    def test_ingestion_and_concept_compass(self) -> None:
        sample_epub = (
            Path(__file__).resolve().parents[2] / "Mnemo" / "pipeline" / "sample" / "sample-book.epub"
        )
        epub_res = ingest_book_file(sample_epub)
        self.assertGreaterEqual(epub_res["chapter_count"], 1)

        md_book = parse_markdown_book(
            "# Chapter 1: Reliable Services\n\n## Rate Limits\n```python\nx = 1\n```\n",
            book_title="Systems Handbook",
        )
        self.assertEqual(md_book["chapter_count"], 1)
        self.assertEqual(len(md_book["chapters"][0]["code_blocks"]), 1)

        # Buzzword lookup: Where Does This Fit?
        for buzzword, expected_node, expected_lab in [
            ("429", "sys:rate_limiting", "rate_limiter"),
            ("cache stampede", "sys:consistent_hashing", "consistent_hashing"),
            ("LSM-tree", "sys:hash_index_compaction", "storage_engine"),
            ("idempotency", "sys:idempotent_webhooks", "webhook_idempotency"),
        ]:
            compass = self.runtime.semantic_memory.where_does_this_fit(buzzword)
            self.assertTrue(compass["matches"], f"Expected match for {buzzword}")
            top = compass["matches"][0]
            self.assertEqual(top["node"]["id"], expected_node)
            self.assertEqual(top["recommended_lab_id"], expected_lab)
            self.assertTrue(top["upstream_prerequisites"], f"Expected prerequisites for {buzzword}")

        missing = self.runtime.semantic_memory.find_missing_links(
            "sys:consistent_hashing", "I know it uses a circle."
        )
        self.assertTrue(any(m["id"] == "sys:data_partitioning" for m in missing))

    # ------------------------------------------------------------------
    # Test 3: Episodic Memory & FSRS-4.5 Scheduler
    # ------------------------------------------------------------------
    def test_episodic_decay_and_fsrs_scheduler(self) -> None:
        now = time.time()
        self.runtime.memory_store.log_episodic_event(
            stage="verification_harness",
            failure_mode_observed="old_failure",
            concept_id="sys:rate_limiting",
            created_at=now - 10 * 86400.0,
        )
        self.runtime.memory_store.log_episodic_event(
            stage="verification_harness",
            failure_mode_observed="recent_failure",
            concept_id="sys:rate_limiting",
            created_at=now - 60.0,
        )
        failures = self.runtime.memory_store.get_recent_failures(concept_id="sys:rate_limiting", now=now)
        self.assertEqual(failures[0]["failure_mode_observed"], "recent_failure")
        self.assertGreater(failures[0]["temporal_decay_weight"], failures[1]["temporal_decay_weight"])

        card = self.runtime.memory_store.create_atomic_card(
            concept_id="sys:rate_limiting",
            front="Why do fixed minute counters allow 2x bursts?",
            back="Quota resets instantaneously at the :00 boundary.",
            due_timestamp=now - 10,
        )
        due = self.runtime.memory_store.get_due_fsrs_cards(now=now)
        self.assertEqual(len(due), 1)

        good = self.runtime.memory_store.schedule_fsrs_review(card["card_id"], rating=3, now=now)
        self.assertGreater(good["stability"], 1.0)
        self.assertGreaterEqual(good["next_interval_days"], 1.0)

        again = self.runtime.memory_store.schedule_fsrs_review(
            card["card_id"], rating=1, now=now + 86400.0
        )
        self.assertEqual(again["lapses"], 1)
        self.assertLess(again["next_interval_days"], 1.0)

    # ------------------------------------------------------------------
    # Test 4: Stage 1 Prime & Stage 2 Active Reader Co-Pilot
    # ------------------------------------------------------------------
    def test_prime_and_copilot_agents(self) -> None:
        briefing = asyncio.run(
            self.runtime.prime.generate_dialogue_briefing(
                PrimeRequest(
                    chapter_title="Storage and Retrieval",
                    chapter_text="Append-only logs make writes fast because sequential disk writes beat random I/O.",
                    concept_id="sys:hash_index_compaction",
                )
            )
        )
        self.assertLess(briefing["generation_ms"], 2000.0)
        self.assertGreaterEqual(len(briefing["dialogue"]), 4)
        self.assertTrue(briefing["schema_teaser"])

        code_res = asyncio.run(
            self.runtime.copilot.generate_code_example(
                "Instead of scanning an append log, maintain an in-memory offset map and compact stale segments.",
                language="python",
                concept_id="sys:hash_index_compaction",
            )
        )
        self.assertIn("class HashIndexedLog", code_res["code"])

        war = asyncio.run(self.runtime.copilot.get_production_war_story("cache stampede under modulo sharding"))
        self.assertIn("Dynamo", war["company_or_system"])

        notes = self.runtime.copilot.generate_margin_notes(
            "A fixed window counter resets every minute. Wait until 00:59 and send 10 requests."
        )
        self.assertGreaterEqual(len(notes), 1)
        self.assertIn("00:59", notes[0]["margin_question"])

    # ------------------------------------------------------------------
    # Test 5: Stage 3 Socratic Diagnostic Agent (Weighted Rubric + Misconceptions)
    # ------------------------------------------------------------------
    def test_socratic_weighted_rubric_and_misconception_loop(self) -> None:
        # Step 1: Answer with misconception triggers anti-pattern classifier + episodic log
        bad_eval = asyncio.run(
            self.runtime.socratic.evaluate_socratic_recall(
                SocraticRequest(
                    concept_id="sys:rate_limiting",
                    question="Why use continuous refill over a per-minute counter?",
                    answer="A fixed window per-minute counter prevents any burst spikes cleanly.",
                    core_points=["refill slots continuously over elapsed time"],
                    invariant_points=["boundary spikes allow 2x traffic across minute edges"],
                    tradeoff_points=["allows bounded bursts capped at capacity"],
                )
            )
        )
        self.assertTrue(bad_eval["misconceptions"])
        self.assertEqual(bad_eval["misconceptions"][0]["fallacy_category"], "fixed_window_boundary_blindness")
        self.assertIsNotNone(bad_eval["follow_up_question"])

        # Step 2: Accurate recall using FakeModel resolves the prior misconception
        self.runtime.socratic.model = FakeModel()
        good_eval = asyncio.run(
            self.runtime.socratic.evaluate_socratic_recall(
                SocraticRequest(
                    concept_id="sys:rate_limiting",
                    question="Why use continuous refill over a per-minute counter?",
                    answer=(
                        "Refill slots continuously over elapsed time because boundary spikes allow 2x traffic "
                        "across minute edges, and it allows bounded bursts capped at capacity."
                    ),
                    core_points=["refill slots continuously over elapsed time"],
                    invariant_points=["boundary spikes allow 2x traffic across minute edges"],
                    tradeoff_points=["allows bounded bursts capped at capacity"],
                )
            )
        )
        self.assertGreaterEqual(good_eval["rubric"]["weighted_total"], 0.85)
        self.assertEqual(good_eval["resolved_prior_misconceptions"], 1)
        self.assertIsNone(good_eval["follow_up_question"])

        truth = self.runtime.socratic.query_book_ground_truth("compaction byte offset", top_k=2)
        self.assertTrue(truth["results"])

    # ------------------------------------------------------------------
    # Test 6: Stage 4 Verification Sandbox & 5-Beat Intuitive Discovery Loop
    # ------------------------------------------------------------------
    def test_sandbox_watchdog_and_import_isolation(self) -> None:
        loop_res = execute_in_sandbox("while True:\n    pass\n", lambda ns: {}, timeout_s=0.35)
        self.assertTrue(loop_res["timed_out"])

        blocked_res = execute_in_sandbox("import os\n", lambda ns: {}, timeout_s=1.0)
        self.assertIn("ImportError", blocked_res["runtime_error"])

    def test_all_four_labs_five_beat_discovery_loop(self) -> None:
        lab_cases = [
            ("rate_limiter", RATE_LIMITER_BEAT1, RATE_LIMITER_BEAT4, "B", ["token bucket"]),
            ("storage_engine", STORAGE_BEAT1, STORAGE_BEAT4, "B", ["bitcask", "lsm-tree", "sstable"]),
            ("consistent_hashing", HASH_BEAT1, HASH_BEAT4, "B", ["consistent hashing", "virtual nodes"]),
            ("webhook_idempotency", WEBHOOK_BEAT1, WEBHOOK_BEAT4, "B", ["idempotency key"]),
        ]
        for lab_id, beat1_code, beat4_code, right_opt, forbidden_jargon in lab_cases:
            with self.subTest(lab=lab_id):
                # Beats 1-4 must strictly mask Beat 5 textbook jargon
                for masked_beat in (1, 2, 3, 4):
                    beat_payload = self.runtime.challenge.get_beat_spec(lab_id, masked_beat)  # type: ignore[arg-type]
                    blob = json.dumps(beat_payload).lower()
                    for term in forbidden_jargon:
                        self.assertNotIn(term, blob, f"Jargon '{term}' leaked in {lab_id} beat {masked_beat}")
                    self.assertNotIn("reveal_content", beat_payload)

                # Beat 1: Obvious naive baseline passes Beat 1 unit tests
                b1 = self.runtime.challenge.run_beat_verification(lab_id, 1, beat1_code, mode="unit_tests")
                self.assertTrue(b1["all_tests_passed"], f"{lab_id} Beat 1 failed: {b1}")
                self.assertEqual(b1["unlocked_beat"], 2)

                # Beat 2: Same naive code breaks inside the visual stress simulator
                b2 = self.runtime.challenge.run_beat_verification(lab_id, 2, beat1_code, mode="stress_simulation")
                trace2 = b2["simulation_trace"]
                self.assertTrue(trace2["failed_as_expected_in_beat2"], f"{lab_id} Beat 2 did not break: {trace2}")
                self.assertTrue(trace2["primitive_payloads"])
                self.assertEqual(b2["unlocked_beat"], 3)

                # Beat 3: Wrong diagnosis rejected; correct diagnosis unlocks Beat 4
                wrong = self.runtime.challenge.submit_diagnosis(lab_id, "A")
                self.assertFalse(wrong["correct"])
                self.assertEqual(wrong["unlocked_beat"], 3)

                right = self.runtime.challenge.submit_diagnosis(lab_id, right_opt)
                self.assertTrue(right["correct"])
                self.assertEqual(right["unlocked_beat"], 4)

                # Beat 4: Evolved code passes both Beat 4 unit tests & stress harness -> unlocks Beat 5
                b4 = self.runtime.challenge.run_beat_verification(lab_id, 4, beat4_code, mode="stress_simulation")
                self.assertTrue(b4["simulation_trace"]["passed_stress_in_beat4"], f"{lab_id} Beat 4 stress failed")
                self.assertTrue(b4["beat4_unit_tests_passed"], f"{lab_id} Beat 4 tests failed")
                self.assertEqual(b4["unlocked_beat"], 5)

                # Beat 5: Reveal unlocked with formal name & book links
                b5 = self.runtime.challenge.get_beat_spec(lab_id, 5)
                self.assertIn("reveal_content", b5)
                self.assertTrue(b5["reveal_content"]["formal_concept_name"])

    # ------------------------------------------------------------------
    # Test 7: Live HTTP & JSON-RPC 2.0 Server Interoperability
    # ------------------------------------------------------------------
    def test_http_and_jsonrpc_server(self) -> None:
        server = make_http_server("127.0.0.1", 0, self.runtime.http_routes, service_name="mnemos-test")
        port = server.server_address[1]
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/health") as resp:
                health = json.loads(resp.read().decode("utf-8"))
                self.assertEqual(health["status"], "ok")

            req = urllib.request.Request(
                f"http://127.0.0.1:{port}/rpc",
                data=json.dumps({"jsonrpc": "2.0", "id": 1, "method": "where_does_this_fit", "params": {"query": "429"}}).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req) as resp:
                rpc = json.loads(resp.read().decode("utf-8"))
                self.assertEqual(rpc["result"]["matches"][0]["recommended_lab_id"], "rate_limiter")
        finally:
            server.shutdown()
            server.server_close()


if __name__ == "__main__":
    unittest.main()
