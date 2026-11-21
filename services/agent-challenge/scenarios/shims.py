"""Pluggable Deterministic Virtual Shim Registry for Verification Sandbox.

Implements ``VirtualClock``, ``VirtualStorage``, ``VirtualNetwork``, ``PartitionHelper``,
and ``VirtualMemory`` as specified in ``doc.md`` Section 3.3, ``left.md`` Task 6.2,
and ``architecture.md`` Section 9.
"""

from __future__ import annotations

import hashlib
import hmac
from collections import OrderedDict
from typing import Any


class VirtualClock:
    """Deterministic virtual clock in milliseconds (accelerates timeouts without sleep)."""

    def __init__(self, initial_ms: int = 0) -> None:
        self._now_ms = initial_ms

    def now(self) -> int:
        return self._now_ms

    def advance(self, delta_ms: int) -> int:
        if delta_ms < 0:
            raise ValueError("VirtualClock cannot advance backwards")
        self._now_ms += delta_ms
        return self._now_ms

    def set_time(self, timestamp_ms: int) -> int:
        self._now_ms = timestamp_ms
        return self._now_ms


class VirtualStorage:
    """Instrumented append-only byte log & virtual disk device."""

    def __init__(self) -> None:
        self._records: list[dict[str, Any]] = []
        self._offsets: dict[int, int] = {}
        self._next_offset: int = 0
        self.read_ops: int = 0
        self.write_ops: int = 0
        self.scan_calls: int = 0
        self.torn_write_enabled: bool = False

    def inject_torn_write(self, enable: bool = True) -> None:
        self.torn_write_enabled = enable

    def reset_metrics(self) -> None:
        self.read_ops = 0
        self.write_ops = 0
        self.scan_calls = 0

    def append(self, key: str, value: str) -> int:
        if self.torn_write_enabled:
            self.torn_write_enabled = False
            raise IOError("Simulated torn disk write before fsync completed")
        offset = self._next_offset
        byte_size = len(key.encode("utf-8")) + len(value.encode("utf-8")) + 8
        entry = {"offset": offset, "byte_size": byte_size, "key": key, "value": value}
        self._offsets[offset] = len(self._records)
        self._records.append(entry)
        self._next_offset += byte_size
        self.write_ops += 1
        return offset

    def read_at(self, offset: int) -> dict[str, Any] | None:
        self.read_ops += 1
        idx = self._offsets.get(offset)
        if idx is None or idx >= len(self._records):
            return None
        return dict(self._records[idx])

    def scan_all(self) -> list[dict[str, Any]]:
        self.scan_calls += 1
        self.read_ops += len(self._records)
        return [dict(r) for r in self._records]

    def rewrite_compacted(self, entries: list[tuple[str, str]] | list[dict[str, str]]) -> None:
        self._records = []
        self._offsets = {}
        self._next_offset = 0
        for item in entries:
            if isinstance(item, dict):
                self.append(item["key"], item["value"])
            else:
                self.append(item[0], item[1])

    def total_bytes(self) -> int:
        return self._next_offset

    def snapshot_segments(self, limit: int = 40) -> list[dict[str, Any]]:
        return [dict(r) for r in self._records[-limit:]]


class VirtualNetwork:
    """Deterministic packet & HTTP webhook network simulator with fault injection."""

    def __init__(self, secret: str = "mnemos-webhook-secret") -> None:
        self._secret = secret.encode("utf-8")
        self.latency_ms: int = 45
        self.packet_loss_rate: float = 0.0
        self.partitioned_nodes: set[str] = set()
        self.drop_next_ack: bool = False
        self.trace_events: list[dict[str, Any]] = []

    def set_latency(self, latency_ms: int) -> None:
        self.latency_ms = max(0, latency_ms)

    def set_packet_loss(self, rate: float) -> None:
        self.packet_loss_rate = min(1.0, max(0.0, rate))

    def partition_node(self, node_id: str, isolated: bool = True) -> None:
        if isolated:
            self.partitioned_nodes.add(node_id)
        else:
            self.partitioned_nodes.discard(node_id)

    def sign_payload(self, timestamp: int, payload_json: str) -> str:
        msg = f"{timestamp}.{payload_json}".encode("utf-8")
        digest = hmac.new(self._secret, msg, hashlib.sha256).hexdigest()
        return f"t={timestamp},v1={digest[:16]}"

    def deliver_webhook(
        self,
        consumer_fn: Any,
        endpoint: str,
        event_id: str,
        amount_cents: int,
        attempt: int,
        clock: VirtualClock,
    ) -> dict[str, Any]:
        ts = clock.now()
        payload = f'{{"event":"payment_intent.succeeded","event_id":"{event_id}","amount":{amount_cents}}}'
        headers = {
            "Host": endpoint,
            "X-Mnemos-Signature": self.sign_payload(ts, payload),
            "Event-ID": event_id,
        }
        if endpoint in self.partitioned_nodes:
            event = {
                "attempt": attempt,
                "timestamp_ms": ts,
                "headers": headers,
                "delivery_status": "partitioned_timeout",
                "http_status": 504,
            }
            self.trace_events.append(event)
            return event

        clock.advance(self.latency_ms)
        consumer_result = consumer_fn(event_id, amount_cents)
        if self.drop_next_ack:
            self.drop_next_ack = False
            event = {
                "attempt": attempt,
                "timestamp_ms": ts,
                "headers": headers,
                "delivery_status": "consumer_ran_ack_dropped",
                "http_status": 504,
                "consumer_result": consumer_result,
            }
        else:
            event = {
                "attempt": attempt,
                "timestamp_ms": ts,
                "headers": headers,
                "delivery_status": "delivered_ack_ok",
                "http_status": 200,
                "consumer_result": consumer_result,
            }
        self.trace_events.append(event)
        return event


class PartitionHelper:
    """Deterministic uniform 32-bit unsigned integer hash helper."""

    @staticmethod
    def hash(value: str) -> int:
        digest = hashlib.sha256(value.encode("utf-8")).digest()
        return int.from_bytes(digest[:4], "big")


class VirtualMemory:
    """Bounded in-memory cache shim tracking hits, misses, and evictions."""

    def __init__(self, capacity: int = 64) -> None:
        self.capacity = max(1, capacity)
        self._store: OrderedDict[str, Any] = OrderedDict()
        self.hits = 0
        self.misses = 0
        self.evictions = 0

    def get(self, key: str) -> Any | None:
        if key not in self._store:
            self.misses += 1
            return None
        self.hits += 1
        self._store.move_to_end(key)
        return self._store[key]

    def set(self, key: str, value: Any) -> None:
        if key in self._store:
            self._store.move_to_end(key)
        elif len(self._store) >= self.capacity:
            self._store.popitem(last=False)
            self.evictions += 1
        self._store[key] = value

    def usage(self) -> dict[str, int]:
        return {
            "entries": len(self._store),
            "capacity": self.capacity,
            "hits": self.hits,
            "misses": self.misses,
            "evictions": self.evictions,
        }


SHIM_FACTORIES: dict[str, Any] = {
    "clock": VirtualClock,
    "storage": VirtualStorage,
    "network": VirtualNetwork,
    "hash": PartitionHelper,
    "memory": VirtualMemory,
}


def build_shims(required_shims: list[str]) -> dict[str, Any]:
    """Instantiate fresh isolated shims declared by a lab."""
    return {shim_id: SHIM_FACTORIES[shim_id]() for shim_id in required_shims if shim_id in SHIM_FACTORIES}
