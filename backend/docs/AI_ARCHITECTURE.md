# EMBEDHUNT AI — AI Architecture

The AI layer enriches an otherwise fully-functional job platform. Every AI
feature degrades gracefully: when `LLM_ENRICHMENT_ENABLED=false` (or Bedrock is
down) the product still works via deterministic fallbacks.

## Architecture

```
                         ┌──────────────────────────────┐
   Mobile / API client   │        FastAPI routes         │
        │                │  app/api/v1/ai_features.py    │
        ▼                │  (ai_guard + rate_limit)      │
 ┌─────────────┐         └───────────────┬──────────────┘
 │ Rate limiter│                         │
 │  (Redis)    │                         ▼
 └─────────────┘             ┌────────────────────────┐
                             │        Agents          │  app/agents/*
                             │ mentor/resume/interview│
                             │ /learning/matching/... │
                             └───────────┬────────────┘
        ContextBuilder ◀────────────────┤ (twin + memory, budget-bounded)
   (owner-asserted, token-capped)       │
                                         ▼
                             ┌────────────────────────┐
                             │        AIRouter        │  app/llm/router.py
                             │ guardrails → cache →    │
                             │ compress → model_select │
                             └───────────┬────────────┘
             ┌───────────────────────────┼───────────────────────────┐
             ▼                           ▼                           ▼
     ┌──────────────┐          ┌──────────────────┐        ┌────────────────┐
     │ SemanticCache│          │  BedrockClient   │        │  CostTracker   │
     │ (redis+mem)  │          │ retries+circuit  │        │ budget + usage │
     └──────────────┘          │ breaker+fallback │        └────────────────┘
                               └──────────────────┘
                                        │
                                        ▼
                                 AWS Bedrock (Claude)
```

## How to add a new AI feature (5 steps)

1. **Pick a `TaskType`** in `app/llm/model_selector.py` (or reuse one). This
   decides the model tier + cost automatically via the routing table.
2. **Add a prompt** in `app/llm/prompts.py` (system prompt + a `render()`
   template) and a Pydantic response model in `app/agents/models.py`.
3. **Add a ContextBuilder method** in `app/llm/context_builder.py` that assembles
   only the fields the prompt needs. Call `_assert_owner(twin, user_id)` when a
   Career Twin is involved.
4. **Add an agent method** on the relevant agent (subclass of `BaseAgent`). Use
   `self._call(task, system, user, max_tokens)` and `self._store_memory(...)`.
5. **Expose a route** in `app/api/v1/ai_features.py` guarded by `ai_guard` and,
   if user-triggered, a `rate_limit(name, max, window)` dependency.

## Model routing table (cost estimates)

USD per 1,000 tokens (input / output). Cost per call ≈
`(in/1000)*in_rate + (out/1000)*out_rate`.

| Task                | Tier   | Input $/1k | Output $/1k | Why |
|---------------------|--------|-----------:|------------:|-----|
| extraction          | Haiku  | 0.001      | 0.005       | Bulk parsing |
| summarization       | Haiku  | 0.001      | 0.005       | Compression |
| matching            | Sonnet | 0.003      | 0.015       | Reasoning over jobs |
| mentoring           | Sonnet | 0.003      | 0.015       | Conversational advice |
| interview           | Sonnet | 0.003      | 0.015       | Q&A evaluation |
| coding              | Sonnet | 0.003      | 0.015       | Code review |
| salary              | Sonnet | 0.003      | 0.015       | Estimation |
| roadmap / planning  | Sonnet | 0.003      | 0.015       | Multi-step plan |
| complex_reasoning   | Opus   | 0.015      | 0.075       | Long career planning only |

**Routing discipline:** Haiku for extraction/summarization/bulk; Sonnet for
explanation/rewrite/interview/roadmap/salary; Opus **only** for long-horizon
career planning. Never call a more expensive tier than the task needs.

## How to add a new agent

1. Create `app/agents/<name>_agent.py` with `class XAgent(BaseAgent)`.
2. In each public method set `self.user_id = user_id` first (drives cost
   tracking + memory ownership).
3. Load twin/memory (parallelize independent reads with `asyncio.gather`),
   build context via `ContextBuilder`, call `self._call(...)`, parse with
   `parse_structured(raw, Model)`, then `self._store_memory(...)`.
4. Wire an endpoint in `ai_features.py`.

## How memory works

- Long-term memory lives in `memory_entries` (see `MemoryRepository`).
- Entries have `memory_type`, `importance_score`, `tags`, optional `expires_at`
  and `conversation_id`.
- Agents write compact summaries (`_store_memory`) and read the most relevant
  entries (`get_relevant(user_id, tags=[...], limit=N)`) — never the full set.
- Conversation turns live in `ai_conversations` via `ConversationManager`.
- Weekly `weekly_memory_cleanup` (Celery) purges expired entries.

## Running without Bedrock

Set `LLM_ENRICHMENT_ENABLED=false`. Then:
- `ai_guard` returns HTTP 503 (`ai_disabled`) for AI-only routes.
- All non-AI features work unchanged.
- Fallbacks (`app/llm/bedrock_client.py::FALLBACK_RESPONSES`) supply safe
  defaults where an AI answer is optional.

With enrichment enabled but Bedrock unreachable, the circuit breaker opens after
5 failures/60s and calls return task-specific fallbacks instead of erroring.

## Environment variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `LLM_ENRICHMENT_ENABLED` | `true` | Master AI toggle |
| `BEDROCK_API_KEY` | — | Required when enrichment on |
| `AWS_REGION` | `us-east-1` | Bedrock region |
| `LLM_MAX_MONTHLY_COST_USD` | `2.0` | Per-user monthly budget |
| `LLM_CACHE_TTL_SECONDS` | `3600` | Default cache TTL |
| `LLM_ENRICHMENT_TIMEOUT_SECONDS` | `10` | Fallback if AI too slow |
| `LLM_HAIKU_MODEL` | `claude-haiku-4-5` | Haiku model id |
| `LLM_SONNET_MODEL` | `claude-sonnet-4-6` | Sonnet model id |
| `LLM_OPUS_MODEL` | `claude-opus-4-8` | Opus model id |
| `REDIS_URL` | `redis://localhost:6379/0` | Cache + rate limiter |

See `BEDROCK_SETUP.md` for provisioning the Bedrock key and model access.
