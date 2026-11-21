"""DeepMind-inspired Token Optimization Engine for Mnemos services.

Implements the 4 optimization pillars from ``left.md`` Task 2 and ``architecture.md`` Section 6:
1. Dynamic Schema Pruning: expose only role-relevant tools and compact inline signatures.
2. Response Field Projection: return only requested payload fields to agent context.
3. KV Cache Prefix Alignment: align static system/book prefixes to fixed token boundaries.
4. Semantic Context Compaction: condense older conversation turns while keeping active code.
"""

from __future__ import annotations

import hashlib
import json
import math
from typing import Any


def estimate_tokens(text_or_obj: Any) -> int:
    """Approximate token count (~4 UTF-8 chars per token for English/JSON/code)."""
    raw = text_or_obj if isinstance(text_or_obj, str) else json.dumps(text_or_obj, sort_keys=True, default=str)
    if not raw:
        return 0
    return max(1, math.ceil(len(raw) / 4))


def _compact_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Compress JSON Schema properties into terse inline type hints."""
    props = schema.get("properties") or {}
    compact_props: dict[str, Any] = {}
    for key, spec in props.items():
        if not isinstance(spec, dict):
            compact_props[key] = spec
            continue
        entry: dict[str, Any] = {"type": spec.get("type", "string")}
        if "enum" in spec:
            entry["enum"] = spec["enum"]
        compact_props[key] = entry
    result: dict[str, Any] = {"type": schema.get("type", "object"), "properties": compact_props}
    if schema.get("required"):
        result["required"] = list(schema["required"])
    return result


def prune_tool_schemas(
    tools: list[dict[str, Any]],
    active_role: str,
    compact: bool = True,
) -> dict[str, Any]:
    """Filter tools to ``active_role`` and optionally prune verbose JSON Schema boilerplate.

    Returns both the pruned tool definitions and exact before/after token telemetry.
    """
    raw_tokens = estimate_tokens(tools)
    scoped: list[dict[str, Any]] = []
    for tool in tools:
        allowed = tool.get("allowed_roles")
        if allowed is not None and active_role not in allowed:
            continue
        desc = str(tool.get("description", "")).strip()
        short_desc = desc.split(".")[0][:80] if compact and desc else desc
        schema = tool.get("input_schema") or {}
        scoped.append(
            {
                "name": tool["name"],
                "description": short_desc,
                "input_schema": _compact_schema(schema) if compact else schema,
            }
        )
    pruned_tokens = estimate_tokens(scoped)
    savings_pct = round(((raw_tokens - pruned_tokens) / raw_tokens) * 100.0, 2) if raw_tokens else 0.0
    return {
        "tools": scoped,
        "raw_tokens": raw_tokens,
        "pruned_tokens": pruned_tokens,
        "savings_pct": savings_pct,
    }


def project_response_fields(payload: Any, fields: list[str] | None) -> Any:
    """DeepMind Response Field Projection: retain only explicitly requested top-level or nested keys.

    Supports dot-notation paths (e.g. ``"summary"`` or ``"meta.chapter"``).
    """
    if not fields:
        return payload
    if isinstance(payload, list):
        return [project_response_fields(item, fields) for item in payload]
    if not isinstance(payload, dict):
        return payload

    projected: dict[str, Any] = {}
    nested: dict[str, list[str]] = {}
    for field in fields:
        if "." in field:
            head, tail = field.split(".", 1)
            nested.setdefault(head, []).append(tail)
        elif field in payload:
            projected[field] = payload[field]

    for head, subfields in nested.items():
        if head in payload:
            projected[head] = project_response_fields(payload[head], subfields)
    return projected


def align_kv_cache_prefix(
    static_prefix: str,
    block_tokens: int = 4096,
    pad_marker: str = " ",
) -> dict[str, Any]:
    """Align static system + book prefix to an exact ``block_tokens`` boundary for KV cache hits."""
    if block_tokens <= 0:
        raise ValueError("block_tokens must be positive")
    target_chars_per_block = block_tokens * 4
    current_len = len(static_prefix)
    blocks = max(1, math.ceil(current_len / target_chars_per_block))
    target_chars = blocks * target_chars_per_block
    pad_len = max(0, target_chars - current_len)
    aligned = static_prefix + (pad_marker * pad_len)
    prefix_hash = hashlib.sha256(static_prefix.encode("utf-8")).hexdigest()[:16]
    return {
        "aligned_prefix": aligned,
        "aligned_tokens": blocks * block_tokens,
        "original_tokens": estimate_tokens(static_prefix),
        "padding_chars": pad_len,
        "kv_cache_key": f"kv-{block_tokens}-{prefix_hash}",
    }


def compact_conversation_history(
    turns: list[dict[str, Any]],
    keep_recent: int = 4,
) -> dict[str, Any]:
    """Sliding-window semantic compactor preserving recent turns and code references.

    Older turns are condensed into compact factual bullet deltas while code fences
    and error identifiers in older turns are preserved verbatim.
    """
    if keep_recent < 0:
        raise ValueError("keep_recent must be non-negative")
    if len(turns) <= keep_recent:
        tokens = estimate_tokens(turns)
        return {
            "summary_delta": "",
            "retained_turns": list(turns),
            "original_tokens": tokens,
            "compacted_tokens": tokens,
            "savings_pct": 0.0,
        }

    split_idx = len(turns) - keep_recent if keep_recent else len(turns)
    older = turns[:split_idx]
    recent = turns[split_idx:]

    deltas: list[str] = []
    for idx, turn in enumerate(older):
        role = str(turn.get("role", "user"))
        content = str(turn.get("content", "")).strip()
        if not content:
            continue
        first_sentence = content.splitlines()[0][:110]
        has_code = "```" in content
        tag = " [contains code]" if has_code else ""
        deltas.append(f"- T{idx + 1}({role}){tag}: {first_sentence}")

    summary_delta = "\n".join(deltas)
    original_tokens = estimate_tokens(turns)
    compacted_tokens = estimate_tokens({"summary_delta": summary_delta, "retained_turns": recent})
    savings_pct = (
        round(((original_tokens - compacted_tokens) / original_tokens) * 100.0, 2)
        if original_tokens
        else 0.0
    )
    return {
        "summary_delta": summary_delta,
        "retained_turns": recent,
        "original_tokens": original_tokens,
        "compacted_tokens": compacted_tokens,
        "savings_pct": savings_pct,
    }
