"""EMBEDHUNT AI — Orchestrator task routing matrix.

Explicitly encodes which task types the mid-tier hosted open-model engine is
ALLOWED to attempt before escalating to Claude, and which must SKIP the hosted
model entirely and go straight to Claude. This gate is an allowlist: only tasks
in ``HOSTED_MODEL_ALLOWED_TASKS`` are ever offered to the hosted engine — every
other task (the Claude-only list below, plus anything unrecognised) bypasses it.

Rationale (per the Phase 3 routing matrix):

* Hosted-eligible — structured/extractive or draft-quality work where a strong
  open model (Llama 3.3 70B) is usually good enough and much cheaper.
* Claude-only — high-stakes, nuanced, or user-facing advisory work where quality
  and safety matter more than cost, so we never risk the cheaper model.
"""
from __future__ import annotations

# Tasks the hosted open model may attempt (allowlist). A low-confidence result
# still escalates to Claude via the confidence gate in hosted_model_engine.
HOSTED_MODEL_ALLOWED_TASKS: frozenset[str] = frozenset(
    {
        "resume_parsing",
        "company_summary",
        "job_description_extraction",
        "skill_extraction",
        "roadmap_draft",
        "coding_review_explanation",
        # Phase 4 migration: templated/lower-stakes generation on the open tier.
        "match_explanation",
        "mentor_daily_brief",
        "resume_score",
        "interview_questions",
        "lesson_generation",
        "flashcard_generation",
        "coding_challenge",
        "memory_summarize",
        "conversation_summarize",
    }
)

# Tasks that must never touch the hosted model — routed straight to Claude.
CLAUDE_ONLY_TASKS: frozenset[str] = frozenset(
    {
        "resume_rewrite",
        "mentor_chat",
        "interview_evaluation",
        "negotiation_advice",
        "gap_analysis_explanation",
        "salary_estimate",  # money advice → high stakes
    }
)

# Hosted-eligible tasks whose output is expected to be structured JSON; the
# confidence heuristic validates JSON parseability for these (vs. a freeform
# sanity check for the rest).
STRUCTURED_OUTPUT_TASKS: frozenset[str] = frozenset(
    {
        "resume_parsing",
        "job_description_extraction",
        "skill_extraction",
        "match_explanation",     # JobMatch JSON
        "mentor_daily_brief",    # DailyBrief JSON
        "resume_score",          # ResumeScore JSON
        "interview_questions",   # QuestionList JSON
        "lesson_generation",     # Lesson JSON
        "flashcard_generation",  # FlashcardList JSON
        "coding_review_explanation",  # CodeReview JSON
        "coding_challenge",           # CodingChallenge JSON
        "roadmap_draft",              # Roadmap JSON
    }
)

# Guard against a task accidentally appearing in both lists.
assert not (HOSTED_MODEL_ALLOWED_TASKS & CLAUDE_ONLY_TASKS), "task cannot be both hosted-allowed and Claude-only"

# ── Open-model fleet: which open model handles which task ────────────────────
# The "Local LLMs" tier is a fleet, not one model: Qwen / Llama / Gemma / Mistral,
# picked per task by strength. Values are OpenAI-compatible model IDs. They are
# the DEFAULT (Together AI) IDs — VERIFY PERIODICALLY at https://www.together.ai/models
# and swap for local IDs (e.g. "qwen2.5:72b", "gemma2:27b") when
# OPEN_MODEL_PROVIDER=local points at an Ollama/vLLM server. Tasks not listed
# fall back to the engine's default model.
QWEN = "Qwen/Qwen2.5-72B-Instruct-Turbo"
LLAMA = "meta-llama/Llama-3.3-70B-Instruct-Turbo"
GEMMA = "google/gemma-2-27b-it"
MISTRAL = "mistralai/Mixtral-8x7B-Instruct-v0.1"

OPEN_MODEL_TASK_MODELS: dict[str, str] = {
    "resume_parsing": QWEN,                 # strong structured extraction
    "skill_extraction": QWEN,               # entity/structured extraction
    "job_description_extraction": LLAMA,    # long-context extraction
    "company_summary": GEMMA,               # concise freeform summary
    "roadmap_draft": MISTRAL,               # cheap draft generation
    "coding_review_explanation": LLAMA,     # code-aware explanation
    "match_explanation": LLAMA,             # structured match reasoning
    "mentor_daily_brief": MISTRAL,          # cheap templated daily brief
    "resume_score": QWEN,                   # structured ATS/fit scoring
    "interview_questions": QWEN,            # question generation
    "lesson_generation": QWEN,              # teaching content
    "flashcard_generation": GEMMA,          # cheap card generation
    "coding_challenge": QWEN,               # challenge authoring
    "memory_summarize": GEMMA,              # internal memory compaction
    "conversation_summarize": GEMMA,        # internal transcript compaction
}


def model_for_task(task: str, default: str) -> str:
    """Open model assigned to ``task``, or ``default`` when unlisted."""
    return OPEN_MODEL_TASK_MODELS.get(task, default)


def is_hosted_allowed(task: str) -> bool:
    """True only if ``task`` is on the hosted-model allowlist."""
    return task in HOSTED_MODEL_ALLOWED_TASKS


def is_claude_only(task: str) -> bool:
    """True if ``task`` is explicitly pinned to Claude (documentation/telemetry)."""
    return task in CLAUDE_ONLY_TASKS


def is_structured_output(task: str) -> bool:
    """True if the hosted model's output for ``task`` should parse as JSON."""
    return task in STRUCTURED_OUTPUT_TASKS
