"""KV-aligned prompts for Stage 2 Active Reading Co-Pilot developer actions."""

from __future__ import annotations

from mnemos_services.common import bootstrap_services
from mnemos_services.common.optimizer import align_kv_cache_prefix

bootstrap_services()

from neuralloop_books import prompts as nl_prompts  # noqa: E402

COPILOT_SYSTEM = (
    "You are an in-situ engineering reading co-pilot. You help software engineers turn dense "
    "textbook passages into minimal executable code, real production post-mortem lessons, "
    "critical trade-off audits, and brief Socratic margin whispers. Reply with JSON only."
)

SHOW_ME_IN_CODE = (
    "Translate this passage into a clean 15-25 line runnable {language} snippet using standard library only.\n"
    "Context notes: {memory_notes}\n"
    'JSON: {{"title":"...","code":"...","walkthrough":["..."]}}'
)

WAR_STORY_PROMPT = (
    "Identify a real-world production incident or engineering architecture (e.g., RocksDB, Kafka, Stripe, "
    "Cloudflare, DynamoDB) illustrating the failure mode in this passage.\n"
    'JSON: {{"concept":"...","company_or_system":"...","incident_summary":"...","root_cause":"...","engineering_lesson":"..."}}'
)

DEVILS_ADVOCATE_PROMPT = (
    "Interrogate the claims in this passage: what did the design sacrifice, and how does it break under "
    "hardware faults, burst traffic, or network partitions?\n"
    'JSON: {{"claim_examined":"...","sacrificed_properties":["..."],"failure_modes_under_fault":["..."],"when_not_to_use":"..."}}'
)


def build_copilot_prompt(section_text: str, task_prompt: str) -> dict[str, str]:
    aligned = align_kv_cache_prefix(COPILOT_SYSTEM)
    return {
        "system": aligned["aligned_prefix"],
        "kv_cache_key": aligned["kv_cache_key"],
        "source": nl_prompts.wrap_chapter(section_text[:4500]),
        "prompt": task_prompt,
    }
