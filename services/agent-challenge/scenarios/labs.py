"""General 5-Beat Discovery Engine & 4 Illustrative Systems Labs.

Strictly enforces 'Intuition First, Jargon Last': formal textbook names and buzzwords
are masked in Beats 1-4 and revealed only in Beat 5 once the learner co-invents and
verifies the mechanism.
"""

from __future__ import annotations

from typing import Any, Callable

from ..models.schemas import (
    ChallengeExecutionResult,
    DiagnosisOption,
    DiagnosisPrompt,
    LabBeatNumber,
    LabBeatSpec,
    LabDefinition,
    PrimitiveTracePayload,
    SimulationTrace,
    UnitTestResult,
    UnitTestSpec,
    VisualizerMetric,
)
from .sandbox import execute_in_sandbox
from .shims import PartitionHelper, VirtualClock, VirtualNetwork, VirtualStorage


class _LedgerShim:
    """Instrumented ledger used by the Webhook Delivery lab."""

    def __init__(self) -> None:
        self.charges: list[dict[str, Any]] = []

    def charge(self, event_id: str, amount_cents: int) -> dict[str, Any]:
        entry = {"charge_num": len(self.charges) + 1, "event_id": event_id, "amount_cents": amount_cents}
        self.charges.append(entry)
        return entry


# ---------------------------------------------------------------------------
# Lab 1: Traffic Control & Backpressure
# ---------------------------------------------------------------------------

RATE_LIMITER_STARTER = """class RequestGuard:
    def __init__(self, max_per_minute: int, clock):
        self.max_per_minute = max_per_minute
        self.clock = clock
        self.counts = {}

    def allow_request(self, client_id: str) -> bool:
        # Beat 1: Implement the simplest per-minute counter
        minute_bucket = self.clock.now() // 60000
        key = (client_id, minute_bucket)
        used = self.counts.get(key, 0)
        if used >= self.max_per_minute:
            return False
        self.counts[key] = used + 1
        return True
"""


def _run_rate_limiter_tests(ns: dict[str, Any], beat: int) -> dict[str, Any]:
    cls = ns.get("RequestGuard")
    if cls is None:
        return {"runtime_error": "Class `RequestGuard` must be defined."}
    results: list[dict[str, Any]] = []

    def check(test_id: str, name: str, hint: str, fn: Callable[[], None]) -> None:
        try:
            fn()
            results.append({"test_id": test_id, "name": name, "passed": True, "message": "Passed"})
        except AssertionError as exc:
            results.append(
                {
                    "test_id": test_id,
                    "name": name,
                    "passed": False,
                    "message": str(exc) or "Expectation failed",
                    "socratic_hint": hint,
                }
            )

    def t1() -> None:
        clk = VirtualClock(1000)
        g = cls(10, clk)
        for i in range(10):
            assert g.allow_request("c1") is True, f"Expected request {i + 1}/10 to be allowed"

    def t2() -> None:
        clk = VirtualClock(1000)
        g = cls(10, clk)
        for _ in range(10):
            g.allow_request("c1")
        clk.advance(1000)
        assert g.allow_request("c1") is False, "Expected 11th request in same minute to be blocked"

    def t3() -> None:
        clk = VirtualClock(1000)
        g = cls(10, clk)
        for _ in range(10):
            g.allow_request("c1")
        clk.set_time(65000)
        assert g.allow_request("c1") is True, "Expected quota to recover in the next minute"

    def t4() -> None:
        clk = VirtualClock(1000)
        g = cls(10, clk)
        for _ in range(10):
            g.allow_request("c1")
        assert g.allow_request("c1") is False
        assert g.allow_request("c2") is True, "Blocking one client must not block another client"

    check("allows_within_limit", "Allows within limit", "Check your initial counter allowance.", t1)
    check("blocks_excess", "Blocks excess in same minute", "Block once count reaches max_per_minute.", t2)
    check("resets_next_minute", "Recovers over time", "Allow new requests after time advances.", t3)
    check("isolates_clients", "Isolates per client", "Store state keyed by `client_id`.", t4)

    if beat >= 4:
        def t5() -> None:
            clk = VirtualClock(59000)
            g = cls(10, clk)
            allowed = sum(1 for _ in range(10) if g.allow_request("c1"))
            clk.set_time(61000)
            allowed += sum(1 for _ in range(10) if g.allow_request("c1"))
            assert allowed <= 11, f"Allowed {allowed} requests in 2 seconds across minute boundary (must be <= 11)"

        def t6() -> None:
            clk = VirtualClock(0)
            g = cls(10, clk)
            for _ in range(10):
                g.allow_request("c1")
            clk.advance(12000)  # 12s -> 2 slots at 10/60s
            assert g.allow_request("c1") is True, "Expected 1st dripped slot after 12s"
            assert g.allow_request("c1") is True, "Expected 2nd dripped slot after 12s"
            assert g.allow_request("c1") is False, "Expected 3rd request blocked (only 2 slots refilled in 12s)"

        def t7() -> None:
            clk = VirtualClock(0)
            g = cls(10, clk)
            clk.advance(600000)  # idle 10 minutes
            allowed = sum(1 for _ in range(15) if g.allow_request("c1"))
            assert allowed == 10, f"Expected burst cap of 10 after idle period, got {allowed}"

        check(
            "blocks_boundary_double_spike",
            "Stops boundary 2x burst",
            "Refill gradually from elapsed milliseconds instead of resetting full quota at :00.",
            t5,
        )
        check(
            "steady_drip_recovery",
            "Refills smoothly at 1 slot per 6s",
            "Compute refill = (elapsed_ms / 60000.0) * max_per_minute.",
            t6,
        )
        check(
            "caps_at_maximum_capacity",
            "Caps stored burst at max_per_minute",
            "Use min(self.max_per_minute, current + refill).",
            t7,
        )

    return {"unit_test_results": results, "all_tests_passed": all(r["passed"] for r in results)}


def _run_rate_limiter_stress(ns: dict[str, Any], beat: int) -> dict[str, Any]:
    cls = ns.get("RequestGuard")
    if cls is None:
        return {"runtime_error": "Class `RequestGuard` must be defined."}

    clk = VirtualClock(59000)
    guard = cls(10, clk)
    events: list[dict[str, Any]] = []

    for idx in range(10):
        ok = bool(guard.allow_request("burst-client"))
        events.append({"t_ms": clk.now(), "label": "00:59", "seq": idx + 1, "allowed": ok})

    clk.set_time(61000)
    for idx in range(10):
        ok = bool(guard.allow_request("burst-client"))
        events.append({"t_ms": clk.now(), "label": "01:01", "seq": idx + 11, "allowed": ok})

    allowed_total = sum(1 for e in events if e["allowed"])
    blocked_total = len(events) - allowed_total
    db_load_pct = round((allowed_total / 10.0) * 100.0, 1)
    crashed = allowed_total > 11

    alert = (
        {
            "severity": "critical",
            "title": "DATABASE OVERLOAD CRASH",
            "detail": f"{allowed_total}/20 requests passed within 2 seconds across 00:59 -> 01:01 ({db_load_pct}% capacity).",
        }
        if crashed
        else {
            "severity": "healthy",
            "title": "BURST SMOOTHED SAFELY",
            "detail": f"Only {allowed_total}/20 requests reached the DB ({blocked_total} throttled at 429).",
        }
    )
    trace = {
        "scenario_name": "boundary_double_burst",
        "failed_as_expected_in_beat2": (beat == 2 and crashed),
        "passed_stress_in_beat4": (beat >= 4 and not crashed),
        "headline_alert": alert,
        "metrics": [
            {"label": "Peak 2s Requests Allowed", "value": allowed_total, "status": "critical" if crashed else "healthy"},
            {"label": "Requests Rejected", "value": blocked_total, "status": "healthy" if not crashed else "warning"},
            {"label": "DB Burst Load %", "value": db_load_pct, "status": "critical" if crashed else "healthy"},
        ],
        "primitive_payloads": [
            {"primitive": "timeline_stream", "data": {"events": events, "safe_burst_limit": 10}},
            {"primitive": "metric_gauge", "data": {"load_pct": db_load_pct, "threshold_pct": 110}},
        ],
    }
    return {"simulation_trace": trace}


# ---------------------------------------------------------------------------
# Lab 2: Storage Engines & Fast Retrieval
# ---------------------------------------------------------------------------

STORAGE_ENGINE_STARTER = """class MiniKVStore:
    def __init__(self, disk):
        self.disk = disk

    def set(self, key: str, value: str) -> None:
        # Beat 1: Append sequentially for fast writes
        self.disk.append(key, value)

    def get(self, key: str):
        # Beat 1: Scan backwards to find the newest record
        for entry in reversed(self.disk.scan_all()):
            if entry["key"] == key:
                return entry["value"]
        return None

    def compact(self) -> None:
        # Used in Beat 4 to reclaim stale overwritten entries
        pass
"""


def _run_storage_tests(ns: dict[str, Any], beat: int) -> dict[str, Any]:
    cls = ns.get("MiniKVStore")
    if cls is None:
        return {"runtime_error": "Class `MiniKVStore` must be defined."}
    results: list[dict[str, Any]] = []

    def check(test_id: str, name: str, hint: str, fn: Callable[[], None]) -> None:
        try:
            fn()
            results.append({"test_id": test_id, "name": name, "passed": True, "message": "Passed"})
        except AssertionError as exc:
            results.append(
                {
                    "test_id": test_id,
                    "name": name,
                    "passed": False,
                    "message": str(exc) or "Expectation failed",
                    "socratic_hint": hint,
                }
            )

    def t1() -> None:
        disk = VirtualStorage()
        kv = cls(disk)
        kv.set("user:1", "Alice")
        assert kv.get("user:1") == "Alice", "Expected to retrieve written value"

    def t2() -> None:
        disk = VirtualStorage()
        kv = cls(disk)
        kv.set("k", "v1")
        kv.set("k", "v2")
        assert kv.get("k") == "v2", "Expected latest overwrite to win"

    def t3() -> None:
        disk = VirtualStorage()
        kv = cls(disk)
        assert kv.get("missing") is None, "Missing key must return None"

    check("set_and_get_basic", "Stores and retrieves key", "Append (key, value) to disk and return value.", t1)
    check("overwrites_return_latest", "Overwrites return newest value", "Return the most recent write for a key.", t2)
    check("missing_key_returns_null", "Returns None for missing key", "Return None when key has not been written.", t3)

    if beat >= 4:
        def t4() -> None:
            disk = VirtualStorage()
            kv = cls(disk)
            for i in range(200):
                kv.set(f"k:{i % 20}", f"val:{i}")
            disk.reset_metrics()
            val = kv.get("k:7")
            assert val == "val:187", f"Expected val:187, got {val}"
            assert disk.scan_calls == 0, "get() must NOT call scan_all() once indexed"
            assert disk.read_ops <= 1, f"Expected <= 1 disk hop, got {disk.read_ops}"

        def t5() -> None:
            disk = VirtualStorage()
            kv = cls(disk)
            for i in range(300):
                kv.set(f"hot:{i % 10}", f"payload-{i:04d}")
            before_bytes = disk.total_bytes()
            kv.compact()
            after_bytes = disk.total_bytes()
            assert after_bytes < before_bytes * 0.15, (
                f"Expected compaction to shrink bytes > 85% (before={before_bytes}, after={after_bytes})"
            )
            for i in range(10):
                expected = f"payload-{290 + i:04d}"
                assert kv.get(f"hot:{i}") == expected, f"Lost/corrupted hot:{i} after compaction"

        check(
            "single_hop_reads",
            "Reads jump to byte offset in 1 disk hop",
            "Save `offset = self.disk.append(key, value)` in a dict, and use `self.disk.read_at(offset)` in get().",
            t4,
        )
        check(
            "compaction_reclaims_space",
            "Compaction drops stale writes while preserving latest values",
            "In compact(), gather latest live (key, value) pairs, call `disk.rewrite_compacted(...)`, and rebuild offsets.",
            t5,
        )

    return {"unit_test_results": results, "all_tests_passed": all(r["passed"] for r in results)}


def _run_storage_stress(ns: dict[str, Any], beat: int) -> dict[str, Any]:
    cls = ns.get("MiniKVStore")
    if cls is None:
        return {"runtime_error": "Class `MiniKVStore` must be defined."}

    disk = VirtualStorage()
    kv = cls(disk)
    for i in range(500):
        kv.set(f"hot:{i % 25}", f"v-{i:04d}")

    bytes_before_compact = disk.total_bytes()
    if beat >= 4:
        kv.compact()
    bytes_after_compact = disk.total_bytes()

    disk.reset_metrics()
    for i in range(20):
        val = kv.get(f"hot:{i}")
        if val != f"v-{475 + i:04d}":
            return {"runtime_error": f"Data corruption during stress read for hot:{i}: got {val}"}

    reads_per_lookup = round(disk.read_ops / 20.0, 2)
    slo_breach = reads_per_lookup > 2 or (beat >= 4 and bytes_after_compact >= bytes_before_compact * 0.25)

    alert = (
        {
            "severity": "critical",
            "title": "READ LATENCY SLA BREACH + DISK BLOAT",
            "detail": f"20 reads caused {disk.read_ops} disk ops ({reads_per_lookup}/read) across {bytes_before_compact}B of mostly stale data.",
        }
        if slo_breach
        else {
            "severity": "healthy",
            "title": "1-HOP INDEXED READS & COMPACTED LOG",
            "detail": f"20 reads took {disk.read_ops} disk ops ({reads_per_lookup}/read); disk shrank {bytes_before_compact}B -> {bytes_after_compact}B.",
        }
    )
    trace = {
        "scenario_name": "write_churn_and_reads",
        "failed_as_expected_in_beat2": (beat == 2 and slo_breach),
        "passed_stress_in_beat4": (beat >= 4 and not slo_breach),
        "headline_alert": alert,
        "metrics": [
            {"label": "Disk Ops / Read", "value": reads_per_lookup, "status": "critical" if slo_breach else "healthy"},
            {"label": "Full Log Scans", "value": disk.scan_calls, "status": "critical" if disk.scan_calls else "healthy"},
            {"label": "Disk Bytes", "value": bytes_after_compact, "status": "warning" if slo_breach else "healthy"},
        ],
        "primitive_payloads": [
            {
                "primitive": "state_xray",
                "data": {
                    "segments": disk.snapshot_segments(limit=25),
                    "live_key_count": 25,
                    "bytes_before_compact": bytes_before_compact,
                    "bytes_after_compact": bytes_after_compact,
                },
            },
            {"primitive": "metric_gauge", "data": {"reads_per_lookup": reads_per_lookup, "target_max_hops": 1}},
        ],
    }
    return {"simulation_trace": trace}


# ---------------------------------------------------------------------------
# Lab 3: Distributed Data Partitioning
# ---------------------------------------------------------------------------

CONSISTENT_HASH_STARTER = """class ClusterRouter:
    def __init__(self, initial_nodes: list[str], helper):
        self.helper = helper
        self.nodes = []
        for n in initial_nodes:
            self.add_node(n)

    def add_node(self, node_id: str) -> None:
        if node_id not in self.nodes:
            self.nodes.append(node_id)

    def remove_node(self, node_id: str) -> None:
        if node_id in self.nodes:
            self.nodes.remove(node_id)

    def route_key(self, key: str):
        # Beat 1: Simplest mapping using modulo over active nodes
        if not self.nodes:
            return None
        idx = self.helper.hash(key) % len(self.nodes)
        return self.nodes[idx]
"""


def _run_hash_tests(ns: dict[str, Any], beat: int) -> dict[str, Any]:
    cls = ns.get("ClusterRouter")
    if cls is None:
        return {"runtime_error": "Class `ClusterRouter` must be defined."}
    results: list[dict[str, Any]] = []

    def check(test_id: str, name: str, hint: str, fn: Callable[[], None]) -> None:
        try:
            fn()
            results.append({"test_id": test_id, "name": name, "passed": True, "message": "Passed"})
        except AssertionError as exc:
            results.append(
                {
                    "test_id": test_id,
                    "name": name,
                    "passed": False,
                    "message": str(exc) or "Expectation failed",
                    "socratic_hint": hint,
                }
            )

    def t1() -> None:
        r = cls(["node-1", "node-2", "node-3", "node-4"], PartitionHelper())
        assert r.route_key("user:42") == r.route_key("user:42"), "Routing must be deterministic"

    def t2() -> None:
        r = cls(["node-1", "node-2", "node-3", "node-4"], PartitionHelper())
        seen = {r.route_key(f"session:{i}") for i in range(200)}
        assert seen == {"node-1", "node-2", "node-3", "node-4"}, f"Expected all 4 nodes used, got {seen}"

    def t3() -> None:
        r = cls(["node-1"], PartitionHelper())
        r.remove_node("node-1")
        assert r.route_key("user:1") is None, "Empty cluster must return None"

    check("routes_deterministically", "Routes deterministically", "Same key should always map to same node.", t1)
    check("distributes_across_all_nodes", "Uses all cluster nodes", "Spread keys across all active nodes.", t2)
    check("handles_empty_cluster", "Returns None when empty", "Guard against empty ring/node list.", t3)

    if beat >= 4:
        def t4() -> None:
            r = cls(["node-1", "node-2", "node-3", "node-4"], PartitionHelper())
            keys = [f"k:{i}" for i in range(400)]
            before = {k: r.route_key(k) for k in keys}
            r.remove_node("node-3")
            after = {k: r.route_key(k) for k in keys}
            moved = sum(1 for k in keys if before[k] != after[k])
            healthy_shifted = sum(
                1 for k in keys if before[k] != "node-3" and before[k] != after[k]
            )
            assert moved / len(keys) <= 0.35, f"Moved {moved}/{len(keys)} keys (expected <= 35%)"
            assert healthy_shifted == 0, f"{healthy_shifted} keys owned by surviving nodes moved unexpectedly"

        def t5() -> None:
            r = cls(["node-1", "node-2", "node-3", "node-4"], PartitionHelper())
            keys = [f"k:{i}" for i in range(400)]
            before = {k: r.route_key(k) for k in keys}
            r.add_node("node-5")
            after = {k: r.route_key(k) for k in keys}
            moved = sum(1 for k in keys if before[k] != after[k])
            assert moved / len(keys) <= 0.30, f"Adding 1 node moved {moved}/{len(keys)} keys (expected <= 30%)"

        def t6() -> None:
            r = cls(["node-1", "node-2", "node-3", "node-4"], PartitionHelper())
            counts: dict[str, int] = {}
            for i in range(400):
                owner = r.route_key(f"item:{i}")
                counts[owner] = counts.get(owner, 0) + 1
            for node_id in ("node-1", "node-2", "node-3", "node-4"):
                share = counts.get(node_id, 0) / 400.0
                assert 0.15 <= share <= 0.35, f"Uneven distribution on {node_id}: {share:.1%} (place 20+ markers/node)"

        check(
            "minimal_key_movement_on_removal",
            "Limits key migration when a node fails (<=35%, 0 between healthy nodes)",
            "Stop dividing by len(nodes). Place sorted node markers around a fixed 0..2^32-1 circle.",
            t4,
        )
        check(
            "minimal_key_movement_on_addition",
            "Limits key migration when scaling up (<=30%)",
            "Assign each key clockwise using bisect on the sorted circle of markers.",
            t5,
        )
        check(
            "balanced_distribution",
            "Maintains even load across nodes (15%-35% each)",
            "Place multiple markers per node (e.g. 25 replicas like `f'{node_id}#{i}'`) around the circle.",
            t6,
        )

    return {"unit_test_results": results, "all_tests_passed": all(r["passed"] for r in results)}


def _run_hash_stress(ns: dict[str, Any], beat: int) -> dict[str, Any]:
    cls = ns.get("ClusterRouter")
    if cls is None:
        return {"runtime_error": "Class `ClusterRouter` must be defined."}

    router = cls(["node-1", "node-2", "node-3", "node-4"], PartitionHelper())
    keys = [f"session:{i}" for i in range(400)]
    before = {k: router.route_key(k) for k in keys}
    router.remove_node("node-3")
    after = {k: router.route_key(k) for k in keys}

    moved = sum(1 for k in keys if before[k] != after[k])
    moved_pct = round((moved / len(keys)) * 100.0, 1)
    healthy_shifted = sum(1 for k in keys if before[k] != "node-3" and before[k] != after[k])
    stampede = moved_pct > 35.0 or healthy_shifted > 0

    distribution: dict[str, int] = {}
    for owner in after.values():
        if owner:
            distribution[owner] = distribution.get(owner, 0) + 1

    alert = (
        {
            "severity": "critical",
            "title": f"{moved_pct}% CACHE MISS / DATABASE STAMPEDE",
            "detail": f"Killing 1/4 nodes caused {moved}/400 keys to move ({healthy_shifted} shifted between healthy nodes!).",
        }
        if stampede
        else {
            "severity": "healthy",
            "title": "STAMPEDE PREVENTED",
            "detail": f"Only {moved}/400 keys ({moved_pct}%) migrated from dead node-3; 0 healthy keys moved.",
        }
    )
    trace = {
        "scenario_name": "kill_node_3_chaos",
        "failed_as_expected_in_beat2": (beat == 2 and stampede),
        "passed_stress_in_beat4": (beat >= 4 and not stampede),
        "headline_alert": alert,
        "metrics": [
            {"label": "Keys Migrated %", "value": moved_pct, "status": "critical" if stampede else "healthy"},
            {"label": "Healthy-to-Healthy Moves", "value": healthy_shifted, "status": "critical" if healthy_shifted else "healthy"},
            {"label": "Active Nodes", "value": len(distribution), "status": "healthy"},
        ],
        "primitive_payloads": [
            {
                "primitive": "topology_graph",
                "data": {
                    "killed_node": "node-3",
                    "remaining_distribution": distribution,
                    "moved_count": moved,
                    "total_keys": len(keys),
                },
            },
            {"primitive": "metric_gauge", "data": {"migration_pct": moved_pct, "max_safe_pct": 35.0}},
        ],
    }
    return {"simulation_trace": trace}


# ---------------------------------------------------------------------------
# Lab 4: Reliable Event Processing Under Network Retries
# ---------------------------------------------------------------------------

WEBHOOK_STARTER = """class PaymentWebhookConsumer:
    def __init__(self, ledger):
        self.ledger = ledger

    def handle_delivery(self, event_id: str, amount_cents: int) -> dict:
        # Beat 1: Process the incoming payment event directly
        receipt = self.ledger.charge(event_id, amount_cents)
        return {"status": "processed", "receipt": receipt}
"""


def _run_webhook_tests(ns: dict[str, Any], beat: int) -> dict[str, Any]:
    cls = ns.get("PaymentWebhookConsumer")
    if cls is None:
        return {"runtime_error": "Class `PaymentWebhookConsumer` must be defined."}
    results: list[dict[str, Any]] = []

    def check(test_id: str, name: str, hint: str, fn: Callable[[], None]) -> None:
        try:
            fn()
            results.append({"test_id": test_id, "name": name, "passed": True, "message": "Passed"})
        except AssertionError as exc:
            results.append(
                {
                    "test_id": test_id,
                    "name": name,
                    "passed": False,
                    "message": str(exc) or "Expectation failed",
                    "socratic_hint": hint,
                }
            )

    def t1() -> None:
        ledger = _LedgerShim()
        c = cls(ledger)
        res = c.handle_delivery("evt_1", 4900)
        assert len(ledger.charges) == 1 and res["receipt"]["amount_cents"] == 4900

    def t2() -> None:
        ledger = _LedgerShim()
        c = cls(ledger)
        c.handle_delivery("evt_a", 1000)
        c.handle_delivery("evt_b", 2500)
        assert len(ledger.charges) == 2

    check("processes_valid_payment", "Processes valid payment event", "Call `self.ledger.charge(event_id, amount_cents)`.", t1)
    check("handles_distinct_events", "Handles distinct events independently", "Allow distinct `event_id` deliveries.", t2)

    if beat >= 4:
        def t3() -> None:
            ledger = _LedgerShim()
            c = cls(ledger)
            first = c.handle_delivery("evt_99", 4900)
            second = c.handle_delivery("evt_99", 4900)
            third = c.handle_delivery("evt_99", 4900)
            assert len(ledger.charges) == 1, f"Expected exactly 1 charge on retries, got {len(ledger.charges)}"
            assert second["receipt"] == first["receipt"] and third["receipt"] == first["receipt"]

        check(
            "deduplicates_retried_delivery",
            "Deduplicates retried event deliveries safely",
            "Remember processed `event_id` receipts in a dict before calling `self.ledger.charge(...)`.",
            t3,
        )

    return {"unit_test_results": results, "all_tests_passed": all(r["passed"] for r in results)}


def _run_webhook_stress(ns: dict[str, Any], beat: int) -> dict[str, Any]:
    cls = ns.get("PaymentWebhookConsumer")
    if cls is None:
        return {"runtime_error": "Class `PaymentWebhookConsumer` must be defined."}

    clock = VirtualClock(0)
    net = VirtualNetwork()
    ledger = _LedgerShim()
    consumer = cls(ledger)

    # Attempt 1 runs on server, then ACK drops on network (504 Timeout), triggering exponential retries
    net.drop_next_ack = True
    ev1 = net.deliver_webhook(consumer.handle_delivery, "api.yourapp.com", "evt_998877", 4900, 1, clock)
    clock.advance(2000)
    ev2 = net.deliver_webhook(consumer.handle_delivery, "api.yourapp.com", "evt_998877", 4900, 2, clock)
    clock.advance(4000)
    ev3 = net.deliver_webhook(consumer.handle_delivery, "api.yourapp.com", "evt_998877", 4900, 3, clock)

    charge_count = len(ledger.charges)
    total_cents = sum(c["amount_cents"] for c in ledger.charges)
    duplicated = charge_count != 1

    alert = (
        {
            "severity": "critical",
            "title": f"DUPLICATE CUSTOMER CHARGE (${total_cents / 100:.2f} instead of $49.00)",
            "detail": f"Dropped ACK triggered 2 retries; customer was charged {charge_count} times.",
        }
        if duplicated
        else {
            "severity": "healthy",
            "title": "SAFE RETRY — CHARGED EXACTLY ONCE ($49.00)",
            "detail": "Dropped ACK triggered retries, but duplicate deliveries replayed the saved receipt.",
        }
    )
    trace = {
        "scenario_name": "dropped_ack_retry_storm",
        "failed_as_expected_in_beat2": (beat == 2 and duplicated),
        "passed_stress_in_beat4": (beat >= 4 and not duplicated),
        "headline_alert": alert,
        "metrics": [
            {"label": "Ledger Charges", "value": charge_count, "status": "critical" if duplicated else "healthy"},
            {"label": "Total Billed ($)", "value": round(total_cents / 100.0, 2), "status": "critical" if duplicated else "healthy"},
        ],
        "primitive_payloads": [
            {"primitive": "timeline_stream", "data": {"deliveries": [ev1, ev2, ev3]}},
            {"primitive": "state_xray", "data": {"ledger_entries": ledger.charges}},
            {"primitive": "metric_gauge", "data": {"duplicate_charges": max(0, charge_count - 1)}},
        ],
    }
    return {"simulation_trace": trace}


# ---------------------------------------------------------------------------
# Lab Registry & General 5-Beat Execution Entrypoint
# ---------------------------------------------------------------------------

_LAB_RUNNERS: dict[str, tuple[Callable[[dict[str, Any], int], dict[str, Any]], Callable[[dict[str, Any], int], dict[str, Any]]]] = {
    "rate_limiter": (_run_rate_limiter_tests, _run_rate_limiter_stress),
    "storage_engine": (_run_storage_tests, _run_storage_stress),
    "consistent_hashing": (_run_hash_tests, _run_hash_stress),
    "webhook_idempotency": (_run_webhook_tests, _run_webhook_stress),
}

LAB_DEFINITIONS: dict[str, LabDefinition] = {
    "rate_limiter": LabDefinition(
        id="rate_limiter",
        concept_node_id="sys:rate_limiting",
        title="Protecting a Service From Traffic Spikes",
        required_shims=["clock"],
        visualizer_primitives=["timeline_stream", "metric_gauge"],
        beats={
            1: LabBeatSpec(
                beat=1,
                title="Beat 1: The Obvious Baseline",
                narrative="Your database crashes if any client sends more than 10 requests per minute.",
                instructions="Implement `allow_request(client_id)` using the simplest minute-bucket counter you can write.",
                starter_code=RATE_LIMITER_STARTER,
            ),
            2: LabBeatSpec(
                beat=2,
                title="Beat 2: Watch It Break Under Real Traffic",
                narrative="Your unit tests passed, yet production databases keep crashing. Run the traffic simulator.",
                instructions="Click Run Production Stress to send 10 requests at 00:59 and 10 requests at 01:01.",
                stress_scenario_id="boundary_double_burst",
            ),
            3: LabBeatSpec(
                beat=3,
                title="Beat 3: Spot Why It Broke",
                narrative="Each individual minute respected <= 10 requests, yet 20 requests hit in 2 seconds.",
                instructions="Choose the root cause from what you saw in the stress trace.",
                diagnosis=DiagnosisPrompt(
                    question="Why did 20 requests hit the database in 2 seconds?",
                    options=[
                        DiagnosisOption("A", "clock.now() drifted backwards between calls.", False, "The timeline timestamps moved strictly forward from 59s to 61s."),
                        DiagnosisOption("B", "Resetting the full quota at the :00 minute boundary lets callers stack end-of-minute and start-of-minute traffic back-to-back.", True, "Exactly right! Full-quota resets create a 2x burst window at every minute boundary."),
                        DiagnosisOption("C", "Client IDs collided inside the dictionary.", False, "All 20 requests came from the exact same `burst-client`."),
                    ],
                ),
            ),
            4: LabBeatSpec(
                beat=4,
                title="Beat 4: Make the Smallest Natural Fix",
                narrative="Instead of handing out all 10 request slots at once every :00 tick, refill slots smoothly over elapsed time.",
                instructions="Track remaining slots per client as a float starting at `max_per_minute`. On each call, add `(elapsed_ms / 60000.0) * max_per_minute` capped at `max_per_minute`, then spend 1.0 if >= 1.0.",
            ),
            5: LabBeatSpec(
                beat=5,
                title="Beat 5: Formal Concept & Book Reveal",
                narrative="You just derived a foundational traffic-shaping algorithm from first principles.",
                instructions="Review the formal design, textbook mapping, and real-world footprint.",
                reveal_content={
                    "formal_concept_name": "Token Bucket Rate Limiter",
                    "what_you_invented_summary": "Continuous token replenishment capped at burst capacity eliminates fixed-window boundary doubling while still permitting controlled short bursts.",
                    "book_refs": [
                        {
                            "book_title": "Systems Reliability & Traffic Control (e.g., DDIA Ch. 1 / Computer Networking)",
                            "chapter_label": "Admission Control, Load Shedding & Backpressure",
                            "production_systems": ["Stripe API", "Envoy Proxy", "AWS API Gateway", "Redis"],
                        }
                    ],
                    "next_suggested_nodes": ["sys:idempotent_webhooks"],
                },
            ),
        },
        unit_tests=[
            UnitTestSpec("allows_within_limit", "Allows within limit", "10 requests allowed", 1, "Start quota at max_per_minute."),
            UnitTestSpec("blocks_excess", "Blocks excess", "11th blocked", 1, "Return False when quota exhausted."),
            UnitTestSpec("blocks_boundary_double_spike", "Stops boundary 2x burst", "00:59 + 01:01 spike", 4, "Refill continuously from elapsed_ms."),
        ],
    ),
    "storage_engine": LabDefinition(
        id="storage_engine",
        concept_node_id="sys:hash_index_compaction",
        title="Fast Key-Value Storage & Space Reclamation",
        required_shims=["storage"],
        visualizer_primitives=["state_xray", "metric_gauge"],
        beats={
            1: LabBeatSpec(
                beat=1,
                title="Beat 1: The Obvious Baseline",
                narrative="Appending to the end of a file gives blazing-fast sequential writes.",
                instructions="Implement `set(key, value)` via `disk.append(...)` and `get(key)` by scanning backwards over `disk.scan_all()`.",
                starter_code=STORAGE_ENGINE_STARTER,
            ),
            2: LabBeatSpec(
                beat=2,
                title="Beat 2: Watch Reads & Disk Degrade at Scale",
                narrative="Writes are instant, so let's update 25 keys 500 times and inspect read operations and disk usage.",
                instructions="Run the write-churn & read stress scenario.",
                stress_scenario_id="write_churn_and_reads",
            ),
            3: LabBeatSpec(
                beat=3,
                title="Beat 3: Spot Why It Broke",
                narrative="Your store returned exact values, yet 20 lookups performed 10,000 disk record reads.",
                instructions="Identify the structural bottleneck from the Storage X-Ray.",
                diagnosis=DiagnosisPrompt(
                    question="Why did simple `get()` queries take thousands of disk operations and why did disk keep growing?",
                    options=[
                        DiagnosisOption("A", "disk.append() overwrote the wrong disk sector.", False, "Appends are sequential and fast; write operations stayed O(1)."),
                        DiagnosisOption("B", "Nothing in RAM remembers each key's latest byte offset, forcing full-file scans while old overwrites stay on disk forever.", True, "Spot on! Remembering offsets in RAM makes reads 1 hop, and rewriting live records reclaims stale space."),
                        DiagnosisOption("C", "In-memory dictionaries are slower than scanning disk.", False, "RAM lookups take nanoseconds compared to sequential disk scans."),
                    ],
                ),
            ),
            4: LabBeatSpec(
                beat=4,
                title="Beat 4: Index Offsets in RAM & Reclaim Stale Disk Blocks",
                narrative="Make two natural improvements: jump straight to each key's offset, and drop dead overwrites.",
                instructions="Store `offset = self.disk.append(key, value)` in `self.offsets[key]` so `get()` calls `self.disk.read_at(offset)`. In `compact()`, extract live `(key, latest_value)` pairs, call `self.disk.rewrite_compacted(...)`, and rebuild `self.offsets` from the rewritten records.",
            ),
            5: LabBeatSpec(
                beat=5,
                title="Beat 5: Formal Concept & Book Reveal",
                narrative="You just built the core storage engine architecture used by real-world high-throughput databases.",
                instructions="Explore how this connects to sorted segments and production engines.",
                reveal_content={
                    "formal_concept_name": "Hash-Indexed Append-Only Log (Bitcask Pattern) & Log Compaction",
                    "what_you_invented_summary": "Combining sequential append-only writes with an in-memory key->offset map delivers O(1) disk seeks while background compaction keeps disk bounded.",
                    "book_refs": [
                        {
                            "book_title": "Storage & Retrieval Internals (e.g., DDIA Ch. 3 / Database Internals)",
                            "chapter_label": "Hash Indexes, Compaction & Bridge to SSTables / LSM-Trees",
                            "production_systems": ["Riak Bitcask", "RocksDB", "Apache Kafka", "Cassandra"],
                        }
                    ],
                    "next_suggested_nodes": ["sys:sstable_lsm"],
                },
            ),
        },
        unit_tests=[
            UnitTestSpec("set_and_get_basic", "Basic set & get", "Stores and fetches key", 1, "Use disk.append and scan_all."),
            UnitTestSpec("single_hop_reads", "1-hop indexed reads", "Zero scan_all calls", 4, "Use self.disk.read_at(offset)."),
            UnitTestSpec("compaction_reclaims_space", "Compaction shrinks disk", ">85% space reclaimed", 4, "Use disk.rewrite_compacted."),
        ],
    ),
    "consistent_hashing": LabDefinition(
        id="consistent_hashing",
        concept_node_id="sys:consistent_hashing",
        title="Distributing Keys Across Unreliable Nodes",
        required_shims=["hash"],
        visualizer_primitives=["topology_graph", "metric_gauge"],
        beats={
            1: LabBeatSpec(
                beat=1,
                title="Beat 1: The Obvious Baseline",
                narrative="One server can't hold every user session. Spread keys across 4 nodes using `% len(nodes)`.",
                instructions="Implement `add_node`, `remove_node`, and `route_key` with `helper.hash(key) % len(self.nodes)`.",
                starter_code=CONSISTENT_HASH_STARTER,
            ),
            2: LabBeatSpec(
                beat=2,
                title="Beat 2: Watch What Happens When 1 Node Crashes",
                narrative="400 cached sessions are spread across 4 servers. Let's simulate Node 3 crashing.",
                instructions="Run the Kill Node 3 fault scenario and observe how many keys change owners.",
                stress_scenario_id="kill_node_3_chaos",
            ),
            3: LabBeatSpec(
                beat=3,
                title="Beat 3: Spot Why Healthy Nodes Lost Their Keys",
                narrative="Only 25% of the cluster died, yet ~75% of all keys suddenly moved to different servers.",
                instructions="Diagnose why healthy servers lost keys they already owned.",
                diagnosis=DiagnosisPrompt(
                    question="Why did removing 1 out of 4 servers scramble ~75% of all keys?",
                    options=[
                        DiagnosisOption("A", "helper.hash(key) returns random numbers on each call.", False, "The hash function is 100% deterministic—the same key always produces the exact same integer."),
                        DiagnosisOption("B", "Shrinking `len(nodes)` from 4 to 3 changes the `% N` divisor, altering the remainder for almost every key.", True, "Exactly! Tying key placement to `len(nodes)` invalidates healthy nodes on any resize."),
                        DiagnosisOption("C", "Node 3 initially stored 75% of the keys.", False, "Each of the 4 nodes held ~25% initially."),
                    ],
                ),
            ),
            4: LabBeatSpec(
                beat=4,
                title="Beat 4: Decouple Placement From Cluster Size",
                narrative="Place both keys and servers onto a fixed circular clock from 0 to 2^32 - 1 so removing one server only shifts its own slice.",
                instructions="For each `node_id`, place 25 markers around the circle (`helper.hash(f'{node_id}#{i}')`), keep the sorted list of `(point, node_id)`, and route each key to the first marker >= `helper.hash(key)` (wrapping to index 0).",
            ),
            5: LabBeatSpec(
                beat=5,
                title="Beat 5: Formal Concept & Book Reveal",
                narrative="You just co-invented one of distributed systems' most famous partitioning schemes.",
                instructions="Review how ring partitioning prevents cache stampedes at global scale.",
                reveal_content={
                    "formal_concept_name": "Consistent Hashing with Virtual Nodes (VNodes)",
                    "what_you_invented_summary": "Mapping keys and multiple node replicas onto a fixed hash ring bounds key movement to ~1/N during node failures and balances load evenly.",
                    "book_refs": [
                        {
                            "book_title": "Distributed Data Partitioning (e.g., DDIA Ch. 6 / Dynamo Paper)",
                            "chapter_label": "Partitioning by Hash of Key & Consistent Hashing",
                            "production_systems": ["Amazon DynamoDB", "Apache Cassandra", "Discord", "Envoy Ring Hash"],
                        }
                    ],
                    "next_suggested_nodes": [],
                },
            ),
        },
        unit_tests=[
            UnitTestSpec("routes_deterministically", "Deterministic routing", "Same key -> same node", 1, "Avoid randomness."),
            UnitTestSpec("minimal_key_movement_on_removal", "Minimal churn on node failure", "<=35% moved, 0 between healthy", 4, "Route clockwise on a fixed sorted ring."),
            UnitTestSpec("balanced_distribution", "Balanced node load", "15-35% per node", 4, "Add ~25 marker replicas per node."),
        ],
    ),
    "webhook_idempotency": LabDefinition(
        id="webhook_idempotency",
        concept_node_id="sys:idempotent_webhooks",
        title="Making Payment Retries Safe Over Unreliable Networks",
        required_shims=["network", "clock"],
        visualizer_primitives=["timeline_stream", "state_xray", "metric_gauge"],
        beats={
            1: LabBeatSpec(
                beat=1,
                title="Beat 1: The Obvious Baseline",
                narrative="When a payment webhook event arrives, charge the ledger and return the receipt.",
                instructions="Implement `handle_delivery(event_id, amount_cents)` calling `self.ledger.charge(...)`.",
                starter_code=WEBHOOK_STARTER,
            ),
            2: LabBeatSpec(
                beat=2,
                title="Beat 2: Watch a Dropped Response Double-Charge a Customer",
                narrative="What happens if your server charges the card, but the HTTP 200 OK response drops on the network?",
                instructions="Run the dropped-ACK retry simulation.",
                stress_scenario_id="dropped_ack_retry_storm",
            ),
            3: LabBeatSpec(
                beat=3,
                title="Beat 3: Spot Why Retries Broke Billing",
                narrative="The network retried the exact same event_id after timing out, billing $147.00 instead of $49.00.",
                instructions="Select why retries caused duplicate charges.",
                diagnosis=DiagnosisPrompt(
                    question="Why was the customer charged 3 times for 1 purchase?",
                    options=[
                        DiagnosisOption("A", "The sender changed the event_id on each retry.", False, "Look at the trace headers: all 3 attempts carried `evt_998877`."),
                        DiagnosisOption("B", "The first attempt already executed before the ACK dropped, and the consumer had no memory of processed event IDs.", True, "Yes! Under at-least-once network delivery, consumers must remember processed event IDs."),
                        DiagnosisOption("C", "Exponential backoff ran attempts concurrently.", False, "Attempts ran sequentially at t=0s, 2s, 6s."),
                    ],
                ),
            ),
            4: LabBeatSpec(
                beat=4,
                title="Beat 4: Remember Processed Event Receipts",
                narrative="Before touching the ledger, check whether this `event_id` already completed.",
                instructions="Store `self.processed[event_id] = receipt` so any retried delivery returns the saved receipt without calling `self.ledger.charge` again.",
            ),
            5: LabBeatSpec(
                beat=5,
                title="Beat 5: Formal Concept & Book Reveal",
                narrative="You just built an idempotent consumer resilient to partial network failures.",
                instructions="See how payment systems formalize this pattern.",
                reveal_content={
                    "formal_concept_name": "Idempotency Keys & Effectively-Once Semantics",
                    "what_you_invented_summary": "Combining at-least-once delivery with a deduplicating Idempotency-Key receipt store makes retries safe even when responses drop.",
                    "book_refs": [
                        {
                            "book_title": "Distributed Systems Reliability (e.g., DDIA Ch. 8 & Ch. 11)",
                            "chapter_label": "Unreliable Networks, Timeouts & Idempotency",
                            "production_systems": ["Stripe Webhooks", "Square Payments", "Temporal"],
                        }
                    ],
                    "next_suggested_nodes": [],
                },
            ),
        },
        unit_tests=[
            UnitTestSpec("processes_valid_payment", "Charges valid payment", "Single delivery bills once", 1, "Call self.ledger.charge."),
            UnitTestSpec("deduplicates_retried_delivery", "Deduplicates retries", "3 deliveries -> 1 charge", 4, "Return cached receipt for seen event_id."),
        ],
    ),
}


def execute_lab_beat(
    lab_id: str,
    beat: LabBeatNumber,
    user_code: str,
    mode: str = "unit_tests",
    timeout_s: float = 1.5,
) -> ChallengeExecutionResult:
    """Execute user code in the isolated sandbox for either unit tests or Beat 2/4 stress."""
    lab = LAB_DEFINITIONS.get(lab_id)
    if lab is None:
        raise KeyError(f"Unknown lab_id: {lab_id}")
    test_runner, stress_runner = _LAB_RUNNERS[lab_id]
    driver = stress_runner if mode == "stress_simulation" else test_runner

    raw = execute_in_sandbox(user_code, lambda ns: driver(ns, int(beat)), timeout_s=timeout_s)
    if raw.get("timed_out") or raw.get("compile_error") or raw.get("runtime_error"):
        return ChallengeExecutionResult(
            lab_id=lab_id,
            beat=beat,
            mode=mode,  # type: ignore[arg-type]
            compile_error=raw.get("compile_error"),
            runtime_error=raw.get("runtime_error"),
            timed_out=bool(raw.get("timed_out", False)),
            execution_ms=float(raw.get("execution_ms", 0.0)),
        )

    inner = raw["result"]
    if inner.get("runtime_error"):
        return ChallengeExecutionResult(
            lab_id=lab_id,
            beat=beat,
            mode=mode,  # type: ignore[arg-type]
            runtime_error=inner["runtime_error"],
            execution_ms=float(raw.get("execution_ms", 0.0)),
        )

    if mode == "stress_simulation":
        t = inner["simulation_trace"]
        trace = SimulationTrace(
            scenario_name=t["scenario_name"],
            failed_as_expected_in_beat2=bool(t.get("failed_as_expected_in_beat2", False)),
            passed_stress_in_beat4=bool(t.get("passed_stress_in_beat4", False)),
            headline_alert=t.get("headline_alert"),
            metrics=[VisualizerMetric(**m) for m in t.get("metrics", [])],
            primitive_payloads=[PrimitiveTracePayload(**p) for p in t.get("primitive_payloads", [])],
        )
        return ChallengeExecutionResult(
            lab_id=lab_id,
            beat=beat,
            mode="stress_simulation",
            execution_ms=float(raw.get("execution_ms", 0.0)),
            simulation_trace=trace,
        )

    ut_results = [UnitTestResult(**u) for u in inner.get("unit_test_results", [])]
    return ChallengeExecutionResult(
        lab_id=lab_id,
        beat=beat,
        mode="unit_tests",
        execution_ms=float(raw.get("execution_ms", 0.0)),
        unit_test_results=ut_results,
        all_tests_passed=bool(inner.get("all_tests_passed", False)),
    )
