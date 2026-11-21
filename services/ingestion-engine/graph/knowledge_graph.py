"""Grand Scheme Knowledge Graph builder & Seed Systems Curriculum Pack.

Bridges ``neuralloop_books.book_graph`` with the generalized Concept Compass schema
defined in ``/home/habanera/Documents/Projects/sat-hackathon/doc.md`` (aliases,
plain-English intuition framing before jargon, upstream bottlenecks, trade-offs,
and suggestive book citations).
"""

from __future__ import annotations

import copy
from typing import Any

from mnemos_services.common import bootstrap_services

bootstrap_services()

from neuralloop_books import book_graph as nl_book_graph  # noqa: E402


def build_seed_systems_curriculum() -> dict[str, Any]:
    """Return the curated, book-agnostic Seed Systems Curriculum Graph.

    Book citations are suggestive metadata (e.g. DDIA, OSTEP, Database Internals)
    so the graph structure stays general across books.
    """
    nodes = [
        {
            "id": "sys:service_protection",
            "title": "Service Overload & Backpressure",
            "intuition_title": "Stopping traffic spikes from crashing a server",
            "domain": "resilience",
            "chapter": 1,
            "summary": "Bounding incoming request bursts so downstream databases stay responsive.",
            "why_it_exists": "Unbounded client traffic exhausts connection pools, CPU, and DB locks.",
            "tradeoffs": ["Rejecting excess traffic protects availability vs. dropping spikes"],
            "aliases": [
                {"term": "backpressure", "context_hint": "Slowing callers before queues overflow"},
                {"term": "load shedding", "context_hint": "Dropping excess traffic to stay alive"},
            ],
            "book_refs": [
                {
                    "book_id": "systems-handbook",
                    "book_title": "Foundations of Data-Intensive & Networked Systems (e.g., DDIA Ch. 1)",
                    "chapter_label": "Reliability & Overload Control",
                    "section_summary": "How bounded queues and admission control preserve tail latency.",
                    "production_systems": ["Envoy", "NGINX", "AWS API Gateway"],
                }
            ],
        },
        {
            "id": "sys:rate_limiting",
            "title": "Token Bucket Rate Limiting",
            "intuition_title": "Smoothing spiky requests with a steady slot refill",
            "domain": "resilience",
            "chapter": 1,
            "summary": "Refill request tokens continuously over elapsed time up to a burst cap.",
            "why_it_exists": "Naive fixed-minute counters allow 2x double bursts across minute boundaries.",
            "tradeoffs": [
                "Token Bucket allows controlled bursts vs. Leaky Bucket enforces strict constant rate",
                "Sliding Window Log stores per-request timestamps (exact, higher RAM)",
            ],
            "aliases": [
                {"term": "rate limiting", "context_hint": "Throttling excessive API requests per client"},
                {"term": "429", "context_hint": "HTTP Too Many Requests response returned by rate limiters"},
                {"term": "token bucket", "context_hint": "Continuous refill rate limiter allowing bounded bursts"},
                {"term": "burst traffic", "context_hint": "Boundary spikes that defeat fixed-window counters"},
            ],
            "book_refs": [
                {
                    "book_id": "systems-handbook",
                    "book_title": "Distributed Service Resilience (e.g., DDIA Ch. 1 / Computer Networking)",
                    "chapter_label": "Traffic Shaping & Admission Control",
                    "section_summary": "Why continuous refill eliminates boundary spike amplification.",
                    "production_systems": ["Stripe API", "Envoy Proxy", "Redis Rate Limiter"],
                }
            ],
            "lab_id": "rate_limiter",
        },
        {
            "id": "sys:append_log",
            "title": "Append-Only Write-Ahead Log",
            "intuition_title": "Making writes blazing fast by only adding to the end of a file",
            "domain": "storage",
            "chapter": 3,
            "summary": "Sequential disk appends achieve maximum write throughput and crash safety.",
            "why_it_exists": "Random in-place disk updates require expensive seeks and risk torn writes.",
            "tradeoffs": ["Fast sequential writes vs. slow O(N) full-file reads without an index"],
            "aliases": [
                {"term": "write-ahead log", "context_hint": "Sequential durability log written before mutation"},
                {"term": "append-only log", "context_hint": "Immutable sequential record file"},
            ],
            "book_refs": [
                {
                    "book_id": "storage-internals",
                    "book_title": "Storage & Retrieval Internals (e.g., DDIA Ch. 3 / Database Internals)",
                    "chapter_label": "Log-Structured Storage",
                    "section_summary": "Why sequential I/O dominates random writes on SSDs and HDDs.",
                    "production_systems": ["PostgreSQL WAL", "Kafka", "SQLite WAL"],
                }
            ],
        },
        {
            "id": "sys:hash_index_compaction",
            "title": "Hash-Indexed Log & Compaction (Bitcask / LSM)",
            "intuition_title": "Remembering byte offsets in RAM & cleaning old overwrites",
            "domain": "storage",
            "chapter": 3,
            "summary": "Keep an in-memory key -> byteOffset map for 1-hop reads and compact stale segments.",
            "why_it_exists": "Scanning an entire append-only log degrades reads to O(N) and bloats disk.",
            "tradeoffs": [
                "In-memory hash index gives O(1) point lookups vs. requires keys to fit in RAM",
                "Sorted String Tables (SSTables) enable range scans without storing every key in RAM",
            ],
            "aliases": [
                {"term": "database index", "context_hint": "Auxiliary structure avoiding full log/table scans"},
                {"term": "compaction", "context_hint": "Deduplicating stale overwritten records on disk"},
                {"term": "bitcask", "context_hint": "Log-structured hash-indexed key-value engine"},
                {"term": "lsm-tree", "context_hint": "Log-structured merge tree using memtables and SSTables"},
                {"term": "sstable", "context_hint": "Immutable sorted string table segment flushed from RAM"},
            ],
            "book_refs": [
                {
                    "book_id": "storage-internals",
                    "book_title": "Storage & Retrieval Internals (e.g., DDIA Ch. 3 / Database Internals)",
                    "chapter_label": "Hash Indexes, SSTables & Compaction",
                    "section_summary": "Trading small RAM metadata for O(1) disk seeks and bounded disk usage.",
                    "production_systems": ["Riak Bitcask", "RocksDB", "LevelDB", "Cassandra"],
                }
            ],
            "lab_id": "storage_engine",
        },
        {
            "id": "sys:sstable_lsm",
            "title": "Sorted String Tables (SSTables) & LSM-Trees",
            "intuition_title": "Sorting log segments so range scans stay fast without all keys in RAM",
            "domain": "storage",
            "chapter": 3,
            "summary": "Buffer writes in a sorted Memtable, flush immutable sorted segments, and merge-compact.",
            "why_it_exists": "Hash indexes cannot scan key ranges efficiently and require all keys in RAM.",
            "tradeoffs": ["High write throughput & range queries vs. read/write amplification during merges"],
            "aliases": [
                {"term": "memtable", "context_hint": "In-memory sorted write buffer before disk flush"},
                {"term": "tombstone", "context_hint": "Special deletion marker compacted away asynchronously"},
            ],
            "book_refs": [
                {
                    "book_id": "storage-internals",
                    "book_title": "Storage & Retrieval Internals (e.g., DDIA Ch. 3)",
                    "chapter_label": "SSTables and LSM-Trees",
                    "section_summary": "Sparse indexes + Bloom filters over sorted immutable segments.",
                    "production_systems": ["RocksDB", "ScyllaDB", "Pebble"],
                }
            ],
        },
        {
            "id": "sys:data_partitioning",
            "title": "Horizontal Sharding & Partitioning",
            "intuition_title": "Splitting data across multiple servers when one machine fills up",
            "domain": "distribution",
            "chapter": 6,
            "summary": "Distribute keys across independent nodes so storage and throughput scale horizontally.",
            "why_it_exists": "Single-node RAM, disk, and network bandwidth hit physical hardware ceilings.",
            "tradeoffs": ["Linear write/storage scale vs. cross-shard queries and rebalancing pain"],
            "aliases": [
                {"term": "sharding", "context_hint": "Splitting datasets horizontally across nodes"},
                {"term": "partitioning", "context_hint": "Assigning subsets of keys to specific cluster nodes"},
            ],
            "book_refs": [
                {
                    "book_id": "distributed-systems",
                    "book_title": "Distributed Data Systems (e.g., DDIA Ch. 6)",
                    "chapter_label": "Partitioning",
                    "section_summary": "Key-range vs. hash partitioning and avoiding hot spots.",
                    "production_systems": ["Vitess", "DynamoDB", "MongoDB"],
                }
            ],
        },
        {
            "id": "sys:consistent_hashing",
            "title": "Consistent Hashing & Virtual Nodes",
            "intuition_title": "Placing servers on a fixed circle so losing one node doesn't scramble everything",
            "domain": "distribution",
            "chapter": 6,
            "summary": "Map keys and node replicas onto a 32-bit ring so resizing moves only ~(1/N) keys.",
            "why_it_exists": "Naive `hash(key) % N` shifts ~75% of keys when 1 of 4 nodes fails, causing stampedes.",
            "tradeoffs": ["Minimal rebalancing churn vs. small O(log(N*V)) lookup structure & vnode memory"],
            "aliases": [
                {"term": "consistent hashing", "context_hint": "Ring-based partitioning minimizing key movement"},
                {"term": "cache stampede", "context_hint": "Sudden mass cache misses hammering the primary DB"},
                {"term": "virtual nodes", "context_hint": "Multiple ring points per server for balanced key spread"},
                {"term": "rebalancing", "context_hint": "Migrating ownership cleanly when nodes join or fail"},
            ],
            "book_refs": [
                {
                    "book_id": "distributed-systems",
                    "book_title": "Distributed Data Systems (e.g., DDIA Ch. 6 / Dynamo Paper)",
                    "chapter_label": "Partitioning by Hash & Rebalancing",
                    "section_summary": "Decoupling key placement from cluster size N via hash rings.",
                    "production_systems": ["DynamoDB", "Apache Cassandra", "Discord", "Envoy Ring Hash"],
                }
            ],
            "lab_id": "consistent_hashing",
        },
        {
            "id": "sys:idempotent_webhooks",
            "title": "Idempotency Keys & Exponential Backoff",
            "intuition_title": "Making retries safe when networks drop acknowledgments",
            "domain": "reliability",
            "chapter": 8,
            "summary": "Deduplicate retried requests with an Idempotency-Key ledger and back off smoothly.",
            "why_it_exists": "Timeouts leave callers unsure if a request succeeded; blind retries double-charge.",
            "tradeoffs": ["At-least-once delivery + idempotency key yields effectively-once semantics vs. ledger storage"],
            "aliases": [
                {"term": "idempotency", "context_hint": "Safely applying the same operation once even if retried"},
                {"term": "webhook retry", "context_hint": "Re-delivering failed events with exponential backoff"},
                {"term": "duplicate charge", "context_hint": "Failure mode caused by un-deduplicated payment retries"},
            ],
            "book_refs": [
                {
                    "book_id": "distributed-systems",
                    "book_title": "Distributed Systems Reliability (e.g., DDIA Ch. 8 & Ch. 11)",
                    "chapter_label": "The Trouble with Distributed Systems — Unreliable Networks",
                    "section_summary": "Partial failures, retries, jittered backoff, and idempotency tokens.",
                    "production_systems": ["Stripe Webhooks", "Square", "Temporal"],
                }
            ],
            "lab_id": "webhook_idempotency",
        },
    ]

    edges = [
        {
            "id": "e1",
            "source": "sys:service_protection",
            "target": "sys:rate_limiting",
            "relation": "evolves_into",
            "label": "Naive minute windows fail under bursts ->",
        },
        {
            "id": "e2",
            "source": "sys:append_log",
            "target": "sys:hash_index_compaction",
            "relation": "evolves_into",
            "label": "O(N) log scans & bloat motivate ->",
        },
        {
            "id": "e3",
            "source": "sys:hash_index_compaction",
            "target": "sys:sstable_lsm",
            "relation": "tradeoff",
            "label": "Need range queries & keys > RAM ->",
        },
        {
            "id": "e4",
            "source": "sys:data_partitioning",
            "target": "sys:consistent_hashing",
            "relation": "evolves_into",
            "label": "Modulo % N breaks on node crash ->",
        },
        {
            "id": "e5",
            "source": "sys:service_protection",
            "target": "sys:idempotent_webhooks",
            "relation": "prerequisite",
            "label": "Retries under timeouts require ->",
        },
    ]

    return {
        "version": "1.0.0",
        "kind": "grand_scheme_curriculum",
        "title": "Systems & Data-Intensive Engineering Compass",
        "nodes": nodes,
        "edges": edges,
    }


def merge_chapter_graphs(chapters: list[dict[str, Any]]) -> dict[str, Any]:
    """Build a unified KnowledgeGraph from chapter graph payloads using ``neuralloop_books.book_graph``."""
    raw = nl_book_graph.build(chapters)
    # Normalize nodes so downstream memory-engine services always see aliases/book_refs fields.
    for node in raw.get("nodes", []):
        node.setdefault("intuition_title", node.get("summary") or node.get("name", ""))
        node.setdefault("domain", node.get("layer", "general"))
        node.setdefault("why_it_exists", node.get("detail", ""))
        node.setdefault("tradeoffs", [])
        node.setdefault("aliases", [])
        node.setdefault("book_refs", [])
        node.setdefault("title", node.get("name", node["id"]))
    return raw


def get_active_curriculum(extra_chapters: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Return the Seed Systems Curriculum merged with any ingested book chapter graphs."""
    curriculum = copy.deepcopy(build_seed_systems_curriculum())
    if extra_chapters:
        ingested = merge_chapter_graphs(extra_chapters)
        existing_ids = {n["id"] for n in curriculum["nodes"]}
        for node in ingested.get("nodes", []):
            if node["id"] not in existing_ids:
                curriculum["nodes"].append(node)
                existing_ids.add(node["id"])
        curriculum["edges"].extend(ingested.get("edges", []))
    return curriculum
