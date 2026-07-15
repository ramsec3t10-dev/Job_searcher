# Knowledge Architecture

The **vertical knowledge stack** that grounds the **horizontal AI Orchestrator**.
Sixteen domain layers, in dependency order, are composed per-user into a single
typed `KnowledgeContext`. The orchestrator consumes that context so every AI task
is grounded in what we already know — often meaning *no LLM call at all*.

```
            User
              │
       AI Orchestrator ────────────────┐   (horizontal: routes a task)
              │                         │
   ┌──────────┼──────────┐             │
 Knowledge  Hosted     Claude          │
   Graph    (Together)                 │
              ▲                         │
              │  context["system"]      │
      KnowledgeContext ◄────────────────┘   (vertical: grounds the task)
              ▲
  User → Career Twin → Memory → Knowledge Graph → Skills → Companies → Jobs
  → Projects → Learning → Interview → Market → Salary → Goals → Habits
  → Health (optional) → Professional Growth
```

The two diagrams are one system: the **vertical stack produces** a
`KnowledgeContext`; the **horizontal orchestrator consumes** it.

## Why this exists

Most of these domains already existed in the repo as scattered tables. This
package doesn't duplicate them — it **unifies** them behind one dependency-ordered
assembly so that:

- a service can ask "*what do we know about this user?*" once and get a coherent,
  typed answer;
- the answer grounds orchestrator calls (the hosted/Claude engines read it as a
  system preamble) **without any change to the orchestrator or its engines**;
- deterministic knowledge (the graph, the twin) is surfaced *before* we ever pay
  for an LLM — "the graph already knows the AUTOSAR path."

## The 16 layers

Declared in dependency order in [`layers.py`](layers.py); each is walked
top-to-bottom so a provider can read the layers above it.

| # | Layer | Status | Backing | Reads upstream |
|---|-------|--------|---------|----------------|
| 1 | User | ✅ | `users` + `candidate_profiles` | — |
| 2 | Career Twin | ✅ | `career_twins` | — |
| 3 | Memory | ✅ | `memory_entries` | — |
| 4 | Knowledge Graph | ✅ | `skill_nodes` / `skill_edges` | — |
| 5 | Skills | ✅ | Career Twin skills + graph gaps | twin, graph |
| 6 | Companies | ✅ | `companies` + `job_recommendations` | twin |
| 7 | Jobs | ✅ | `applications` + recs + `discovered_jobs` | — |
| 8 | Projects | ✅ | `career_twins.projects` | twin |
| 9 | Learning | ✅ | `learning_roadmaps` | — |
| 10 | Interview | ✅ | `interview_sessions` + twin | twin |
| 11 | Market | ✅ | `discovered_jobs` (corpus) | — |
| 12 | Salary | ✅ | Career Twin + Market | twin, market |
| 13 | Goals | ✅ | `career_twins.career_goals` | twin |
| 14 | Habits | ✅ | `daily_checkins` + twin | twin |
| 15 | Health *(optional)* | 🔲 planned | — | — |
| 16 | Professional Growth | ✅ | Career Twin + applications | twin |

**Health** is declared but has no backing store yet (the optional layer); the
assembler records it as `skipped: planned`. Adding it later is just a new
provider — no framework change.

## Core types

- **`KnowledgeLayerProvider`** ([`base.py`](base.py)) — one method,
  `async def provide(user_id, session, ctx) -> LayerData | None`. Returns `None`
  when the user has no data for that layer.
- **`LayerData`** — normalised output: `summary` (compact, deterministic,
  **PII-light** digest), `facts` (structured detail), `source`, `confidence`.
- **`KnowledgeContext`** ([`context.py`](context.py)) — one `LayerData` slot per
  loaded layer + `skipped` reasons; typed accessors (`ctx.skills`, `ctx.salary`,
  …); `to_brief()`, `to_system_preamble()`, `to_facts()`.
- **`KnowledgeAssembler`** ([`assembler.py`](assembler.py)) — walks the layers in
  dependency order, best-effort (a failing/empty layer is recorded, never fatal),
  and lets each provider read the already-assembled upstream context.
- **`KnowledgeService`** ([`service.py`](service.py)) — assembles a context and
  turns it into the orchestrator `context` dict.

## Grounding the orchestrator (zero engine changes)

The knowledge brief is passed as `context["system"]`, which the Claude **and**
hosted-model engines already read as their system prompt:

```python
from app.knowledge import KnowledgeService
from app.orchestrator import Orchestrator

ksvc = KnowledgeService()
kctx = await ksvc.build_context(user_id, session)          # assemble the stack
ctx  = KnowledgeService.orchestrator_context(kctx, session=session)  # {user_id, db, system}

result = await Orchestrator().handle("company_summary", payload, ctx)
```

Every routed task is now grounded in the user's real skills, gaps, goals and
market position. The brief is **PII-light by construction** — built from provider
summaries that exclude raw identifiers (name/email/phone) — so it is safe to send
to the third-party hosted model (which also runs its own PII sanitiser).

## Adding / changing a layer

1. **New provider for an existing layer** (e.g. implement Health): add a
   `KnowledgeLayerProvider` subclass, set `layer` / `source`, implement
   `provide`, and register it in
   [`providers/__init__.py`](providers/__init__.py) `default_providers()`. Flip
   the layer's status to `IMPLEMENTED` in [`layers.py`](layers.py).
2. **New layer**: add an enum member (in the right dependency position) and a
   `LayerSpec` in [`layers.py`](layers.py), a typed accessor in
   [`context.py`](context.py), and a provider.

Keep provider `summary` strings **deterministic and PII-light** — that is what
makes the stack cheap, cacheable and safe to feed an LLM.

## Tests

```bash
cd backend
python -m pytest tests/knowledge/ -q
```
