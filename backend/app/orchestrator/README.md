# AI Orchestrator

A single routing layer over every inference backend. Services call the
**`OrchestratorGateway`** (which grounds the task in the user's knowledge stack
and calls `Orchestrator.handle`) **instead of hitting Bedrock directly**, and the
orchestrator resolves each task through a fixed fallthrough chain of pluggable
engines.

> **The app runs on this.** Real call sites are migrated to the gateway
> (`MentorService` → Claude tier; `CompanyIntelligenceService.summarize` →
> open-model tier), and new services should call `get_gateway().run(...)` rather
> than an LLM SDK directly. See **[Adoption](#adoption)** below.

## Fallthrough order

```
rule_engine → knowledge_graph_engine → cache_engine (exact + semantic)
    → open_model_engine (fleet; Together hosted OR local, gated) → claude_engine
```

Each engine implements one method — `async def run(task, payload, context) ->
EngineResult | None` — and either **handles** the task (returns an
`EngineResult`) or **passes** (returns `None`, so the router tries the next
engine).

1. **`rule_engine`** — deterministic, zero-LLM handlers keyed by task name.
   Returns `None` for any unregistered task. Rule results sit *before* the
   cache and are intentionally **not** cached: they are free and deterministic,
   so recomputing is cheaper than a cache round-trip.
2. **`knowledge_graph_engine`** (Phase 2) — deterministic, zero-LLM answers to
   skill-prerequisite, learning-path and role-requirement questions by
   traversing the skill knowledge graph (see
   [`app/models/knowledge_graph.py`](../models/knowledge_graph.py) and
   [`KnowledgeGraphRepository`](../repositories/knowledge_graph_repository.py)).
   Handles the tasks `skill_query` and `learning_path`. It returns an
   `EngineResult` with `confidence=1.0` on a full match, or **`confidence=None`
   (fall through)** when the query names no known node; the router treats
   `confidence=None` (or `None`) as a pass. Like rule results, KG results sit
   *before* the cache and are not written back. It reads a DB session from
   `context["db"]` when present, else opens one from the app session factory.
3. **`cache_engine`** — two-tier cache. **Exact** match keyed by
   `sha256(task + normalized payload JSON)`; on an exact miss it runs a
   **semantic** lookup — embeds the payload text (via `app.ai.embeddings`,
   offline-capable) and returns the nearest previously-cached result for the same
   task above `ORCHESTRATOR_SEMANTIC_CACHE_THRESHOLD` (default `0.92`, tuned for
   the sentence-transformer model). Both tiers use Redis with an in-memory
   fallback.
4. **`open_model_engine`** — mid-tier **open-model fleet** (Qwen / Llama / Gemma
   / Mistral, picked per task by [`task_registry.py`](task_registry.py)) over an
   **OpenAI-compatible** `/chat/completions` endpoint (httpx, async). Provider is
   pluggable over one code path: **`together`** (hosted, default) or **`local`**
   (Ollama/vLLM at `OPEN_MODEL_BASE_URL`, no key). Only attempted for allowlisted
   tasks. After the call it scores a **deliberately simple v1 confidence
   heuristic**; if it clears `ORCHESTRATOR_HOSTED_MODEL_MIN_CONFIDENCE`
   (default `0.6`) the answer is returned, else it returns `confidence=None` and
   the request **escalates to Claude**. Payloads are PII-sanitised before the
   call.
5. **`claude_engine`** — the terminal engine. Adapts the existing
   [`AIRouter`](../llm/router.py) (AWS Bedrock / Anthropic Claude) — no new auth
   or client is introduced. Reuses AIRouter's model selection, guardrails and
   cost tracking.

**Write-back:** every *fresh* (non-cached) result produced downstream of the
cache (a confident hosted answer, or Claude) is written back to `cache_engine`
before it is returned, so an identical subsequent call is served from cache.
Cache hits, rule results and knowledge-graph results are never re-written.

**Cost logging:** every *paid* engine call — the hosted model (including a
low-confidence call that then escalates) and Claude — writes one row to the
`AiUsageLog` table (`orchestrator_usage_log`) when a DB session is available via
`context["db"]` or an injected `usage_session_factory`. Rule/KG/cache results
are free and not logged.

Which engine handled each request is logged via structlog
(`orchestrator_handled`, with `engine=rule|knowledge_graph|cache|hosted_model|claude`).

## Adoption

The app runs on this architecture through **one seam** — the
[`OrchestratorGateway`](gateway.py). A service never touches an LLM SDK; it calls:

```python
from app.orchestrator.gateway import get_gateway

result = await get_gateway().run(
    "company_summary", {"prompt": "..."},
    user_id=user_id, session=db,   # enables knowledge grounding + cost logging
)
```

`gateway.run(...)` (1) assembles the user's `KnowledgeContext` (the vertical
stack), (2) injects a PII-light knowledge brief as `context["system"]` — which
the LLM engines already consume — and an optional persona via `system=`, then
(3) routes through the fallthrough chain.

**Migrated call sites (reference migrations):**

| Service | Task | Tier it lands on |
| --- | --- | --- |
| `MentorService.chat` | `mentor_chat` | Claude (allowlist skips the open model), with deterministic fallback |
| `CompanyIntelligenceService.summarize` | `company_summary` | open-model fleet (Gemma), cache in front, Claude on low confidence |

**To migrate another call site:** replace the direct AI call with
`get_gateway().run(task, payload, user_id=…, session=…)`, choose a task name
(add it to [`task_registry.py`](task_registry.py) if the open model should try
it), and keep any deterministic fallback for resilience.

## Open-model engine (the "Local LLMs" tier)

**Fleet, not one model** — per-task routing in
[`task_registry.py`](task_registry.py) `OPEN_MODEL_TASK_MODELS`:

| Task | Open model |
| --- | --- |
| `resume_parsing`, `skill_extraction` | Qwen 2.5 72B |
| `job_description_extraction`, `coding_review_explanation` | Llama 3.3 70B |
| `company_summary` | Gemma 2 27B |
| `roadmap_draft` | Mixtral 8x7B |

**Provider is pluggable over one OpenAI-compatible code path:**

- `OPEN_MODEL_PROVIDER=together` (default) → hosted open models, key from
  `TOGETHER_API_KEY` (env only). When unset the engine is dormant → straight to Claude.
- `OPEN_MODEL_PROVIDER=local` + `OPEN_MODEL_BASE_URL=http://localhost:11434/v1`
  → a genuinely **self-hosted** fleet on Ollama / vLLM (no key; cost logged as `0`).

**Task-type gating** ([`task_registry.py`](task_registry.py)) — an explicit
allowlist; only these are ever attempted on the open model:

| Hosted-eligible (allowlist)     | Claude-only (skip hosted)      |
| ------------------------------- | ------------------------------ |
| `resume_parsing` *(JSON)*       | `resume_rewrite`               |
| `job_description_extraction` *(JSON)* | `mentor_chat`            |
| `skill_extraction` *(JSON)*     | `interview_evaluation`         |
| `company_summary`               | `negotiation_advice`           |
| `roadmap_draft`                 | `gap_analysis_explanation`     |
| `coding_review_explanation`     |                                |

Any task **not** on the allowlist (including the Claude-only list and any
unknown task) bypasses the hosted model entirely. *(JSON)* tasks are validated
for JSON-parseability by the confidence heuristic; the rest use a length /
truncation / repetition sanity check. **The heuristic is intentionally basic in
v1** and is a placeholder for a real eval-based confidence model later.

**Data governance / PII:** `HostedModelEngine._sanitize_payload` runs before any
Together call — it drops labelled identity keys (`name`, `email`, `phone`,
`linkedin`, …) and redacts inline email/phone patterns from remaining free text,
so raw PII is never sent to the third-party provider unchecked. This v1 pass is
lightweight (labelled keys + regex); a stricter NER-based scrubber is a
follow-up noted in the code.

## `EngineResult`

Every engine returns the same shape ([`engine_base.py`](engine_base.py)):

| field                | type            | meaning                                             |
| -------------------- | --------------- | --------------------------------------------------- |
| `text`               | `str`           | The engine's textual output.                        |
| `engine_used`        | `str`           | e.g. `rule:daily_brief`, `claude:claude-sonnet-4-6`.|
| `confidence`         | `float \| None` | 0–1 confidence; `None` when not meaningful.         |
| `cached`             | `bool`          | `True` when served from a cache.                    |
| `cost_estimate_usd`  | `float \| None` | `0.0` for deterministic engines, `None` if unknown. |

## Usage

```python
from app.orchestrator import Orchestrator

orch = Orchestrator()  # default engines (real rule + Redis cache + Claude)

# Deterministic — handled by the rule engine, never touches the LLM.
brief = await orch.handle(
    "daily_brief",
    {"name": "Ada", "streak_days": 5, "new_matches": 3, "pending_applications": 2},
)

# Anything without a rule handler falls through to cache → Claude.
answer = await orch.handle(
    "summarization",
    {"prompt": "Summarize this job description ..."},
    context={"user_id": "u_123"},  # optional: user_id, system, use_cache
)
```

`context` is optional per-request metadata. Recognised keys today:
`user_id` (attributes LLM cost), `system` (system prompt for Claude),
`use_cache` (toggles AIRouter's own response cache).

## Adding a new **rule handler**

A rule handler is a plain function `(payload: dict, context: dict) -> str`.
Register it on a `RuleEngine` by task name:

```python
from app.orchestrator import Orchestrator, RuleEngine

def weekly_summary(payload: dict, context: dict) -> str:
    return f"You applied to {payload['applications']} roles this week."

rules = RuleEngine()                     # ships with daily_brief + flashcard_schedule
rules.register("weekly_summary", weekly_summary)

orch = Orchestrator(rule_engine=rules)
result = await orch.handle("weekly_summary", {"applications": 12})
# result.engine_used == "rule:weekly_summary"
```

To make it a permanent default, register it inside `RuleEngine.__init__` in
[`rule_engine.py`](rule_engine.py) alongside `daily_brief` and
`flashcard_schedule`. Keep handlers **pure and deterministic** — no I/O, no
model calls; that is the whole point of the rule layer.

## Adding a new **task type** (routed to Claude)

No registration is required — any task string with no rule handler falls through
to the cache and then Claude. To control how the task maps to a model:

- **Model tier & temperature:** the task string is resolved to an
  [`llm.model_selector.TaskType`](../llm/model_selector.py). If your task name
  matches a `TaskType` value it maps directly; otherwise add an alias in
  `_TASK_TYPE_ALIASES` in [`claude_engine.py`](claude_engine.py) (unmapped tasks
  use `SUMMARIZATION`).
- **Cache TTL:** add an entry to `ORCHESTRATOR_CACHE_TTL` in
  [`app/config/settings.py`](../config/settings.py) — `{"my_task": 3600}`. Tasks
  not listed use the 1-day (`86400s`) default; `0` disables caching for the task.

## Knowledge Graph engine (Phase 2)

Answers `skill_query` and `learning_path` tasks deterministically from a small
directed graph of embedded-engineering skills.

**Payload shapes** (all optional keys; the engine also parses a free-text
`query` by keyword-matching known skill/role names — no LLM):

| task            | payload keys                         | example                                             |
| --------------- | ------------------------------------ | --------------------------------------------------- |
| `skill_query`   | `query`, or `skill`, or `role`, `intent` (`prerequisites`/`next`) | `{"query": "what does AUTOSAR require?"}` |
| `learning_path` | `from_skill` + `to_skill`, or `query` | `{"from_skill": "CAN", "to_skill": "AUTOSAR"}`      |

Pass a DB session via `context={"db": session}` when the caller already has one;
otherwise the engine opens its own from the app session factory.

**Schema** ([`app/models/knowledge_graph.py`](../models/knowledge_graph.py)):
`SkillNode(name, category)`, `SkillEdge(from_skill_id, to_skill_id, edge_type)`
where `edge_type ∈ {PREREQUISITE_OF, REQUIRED_BY, COMMONLY_PAIRED_WITH}`, and
`RoleRequirement(role_name, skill_id, required)`. Edge direction: `from →
to` of type `PREREQUISITE_OF` means "learn `from` before `to`".

**Extending the graph:** edit the `NODES`, `EDGES` and `ROLES` tables in
[`database/seeds/knowledge_graph_seed.py`](../../database/seeds/knowledge_graph_seed.py)
and re-run the seed (idempotent — safe to run repeatedly):

```bash
cd backend
python -m database.seeds.knowledge_graph_seed
```

## Cost log schema

`AiUsageLog` ([`app/models/orchestrator_usage.py`](../models/orchestrator_usage.py),
table `orchestrator_usage_log`, migration `c8d9e0f1a2b3`) — one row per paid
engine call, so cost-per-user is queryable for OKR tracking:

| column              | type         | notes                                             |
| ------------------- | ------------ | ------------------------------------------------- |
| `id`                | `str(36)`    | uuid PK (BaseModel)                               |
| `user_id`           | `str(36)`    | indexed; `""` when anonymous                      |
| `task_type`         | `str(60)`    | indexed; the orchestrator task name               |
| `engine_used`       | `str(80)`    | indexed; e.g. `together:…` or `claude:…`          |
| `tokens_in`         | `int`        | prompt tokens                                     |
| `tokens_out`        | `int`        | completion tokens                                 |
| `cost_estimate_usd` | `float`      | tokens × provider price                           |
| `created_at`        | `datetime`   | from `TimestampMixin` (also `updated_at`)         |

Kept separate from the LLM layer's `app.llm.cost_tracker.AIUsageLog`
(table `ai_usage_log`), which is keyed by concrete `model` rather than the
routing-layer `engine_used`.

## Configuration

Defined in [`app/config/settings.py`](../config/settings.py):

| setting                                     | type             | default | purpose                                             |
| ------------------------------------------- | ---------------- | ------- | --------------------------------------------------- |
| `ORCHESTRATOR_ENABLE_CACHE`                 | `bool`           | `True`  | Master on/off switch for the cache layer.           |
| `ORCHESTRATOR_CACHE_TTL`                    | `dict[str, int]` | `{}`    | Per-task cache TTL (seconds); default `86400`.      |
| `ORCHESTRATOR_SEMANTIC_CACHE`               | `bool`           | `True`  | Enable the embedding-similarity cache tier.         |
| `ORCHESTRATOR_SEMANTIC_CACHE_THRESHOLD`     | `float`          | `0.92`  | Min cosine similarity for a semantic hit.           |
| `ORCHESTRATOR_SEMANTIC_CACHE_MAX_PER_TASK`  | `int`            | `500`   | Bound on the per-task embedding index (trimmed + TTL). |
| `OPEN_MODEL_PROVIDER`                        | `str`            | `together` | `together` (hosted) or `local` (Ollama/vLLM).    |
| `OPEN_MODEL_BASE_URL`                        | `str \| None`    | `None`  | Overrides the base URL (e.g. local endpoint).       |
| `OPEN_MODEL_API_KEY`                         | `str \| None`    | `None`  | Overrides the key (local needs none).               |
| `TOGETHER_API_KEY`                          | `str \| None`    | `None`  | Together AI key (env only). Unset → open tier dormant. |
| `TOGETHER_BASE_URL`                         | `str`            | `https://api.together.xyz/v1` | Default provider base URL.    |
| `TOGETHER_MODEL`                            | `str`            | `meta-llama/Llama-3.3-70B-Instruct-Turbo` | Default/fallback open model. |
| `ORCHESTRATOR_ENABLE_HOSTED_MODEL`          | `bool`           | `True`  | Master on/off switch for the open-model engine.     |
| `ORCHESTRATOR_HOSTED_MODEL_MIN_CONFIDENCE`  | `float`          | `0.6`   | Below this, escalate the open-model answer to Claude. |
| `HOSTED_MODEL_TIMEOUT_SECONDS`              | `float`          | `30.0`  | httpx request timeout.                              |
| `HOSTED_MODEL_MAX_TOKENS`                   | `int`            | `1024`  | Max completion tokens.                              |
| `HOSTED_MODEL_TEMPERATURE`                  | `float`          | `0.3`   | Sampling temperature.                               |

> The Phase 3 spec referenced `app/core/config.py`; this repo's settings live in
> [`app/config/settings.py`](../config/settings.py), so the new keys were added
> there.

## Observability (Phase 6)

- **One structured log line per `handle()`** — event `orchestrator_handled` with
  `task`, `engine_used`, `engine` (tier), `cached`, `confidence`, `latency_ms`,
  `cost_estimate_usd` (structlog → JSON in prod; dashboard-ready).
- **Per-tier usage rows** — every handled request writes one `AiUsageLog` row
  tagged with `engine_tier` (rule/kg/cache/hosted/claude), `latency_ms`, cost
  (free tiers = 0). This makes request-share exact.
- **`GET /api/v1/admin/ai-usage`** (platform-admin only) — total cost this month,
  cost + %-requests + avg latency **by engine tier** (the "≤5% to Claude" launch
  KPI = `claude_pct_requests`), and the top-10 highest-cost task types. Sourced
  directly from `AiUsageLog` ([`ai_usage_repository.py`](../repositories/ai_usage_repository.py)).
- **Confidence-heuristic eval** — [`tests/orchestrator/eval/`](../../tests/orchestrator/eval/):
  a labeled set checks the Phase-3 escalation heuristic isn't over/under-escalating
  (`pytest tests/orchestrator/eval/ -s`).

## Tests

```bash
cd backend
python -m pytest tests/orchestrator/ -q
```
