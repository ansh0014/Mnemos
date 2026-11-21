"""Prompt templates for Stage 1 Prime Agent with 4K KV cache alignment."""

from __future__ import annotations

from mnemos_services.common import bootstrap_services
from mnemos_services.common.optimizer import align_kv_cache_prefix

bootstrap_services()

from neuralloop_books import prompts as nl_prompts  # noqa: E402

PRIME_SYSTEM = (
    "You are a Stage 1 Prime briefing synthesizer for software engineers. "
    "Generate a crisp 60-second architectural framing dialogue between Ada (pragmatic backend engineer) "
    "and Theo (staff systems architect), focused on why naive approaches break and what invariant matters. "
    "Return JSON only."
)

PRIME_USER_TEMPLATE = (
    'Prepare a Stage 1 Prime briefing for chapter "{title}".\n'
    "JSON shape: "
    '{{"core_problem_statement":"...",'
    '"dialogue":[{{"speaker":"Ada|Theo","role":"Engineer|Architect","text":"..."}}],'
    '"key_invariants":["..."]}}'
)


def build_prime_prompt(chapter_title: str, chapter_text: str) -> dict[str, str]:
    """Wrap source text safely and align static prefix to 4K token boundary."""
    wrapped = nl_prompts.wrap_chapter(chapter_text[:6000])
    aligned = align_kv_cache_prefix(PRIME_SYSTEM)
    return {
        "system": aligned["aligned_prefix"],
        "kv_cache_key": aligned["kv_cache_key"],
        "source": wrapped,
        "prompt": PRIME_USER_TEMPLATE.format(title=chapter_title),
    }
