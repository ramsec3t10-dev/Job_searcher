# Training capture & distillation pipeline (Phase 5)

The mechanism that lets EMBEDHUNT eventually **run its own models**: turn the
orchestrator's live traffic into a training corpus, evaluate a candidate model
against the incumbent, and promote it per task once it clears the bar — all
without changing agent code (routing is config).

> **Goal:** own your inference, not isolate it. Distill the routine, high-volume
> tasks onto your own small models; keep a thin frontier dependency (Claude) as
> the *teacher* and escalation ceiling.

## The loop

```
every paid engine result
   │  (consent + capture flag)
   ▼
ai_interaction  ── served answer (the reference) + optional shadow candidate
   │
   ├── record_feedback(...)   ← accepted / edited / rating / outcome (applied→interview→offer)
   │
   ├── dataset.export_task()  ← fine-tuning-ready {messages, completion} JSONL
   │        │
   │        ▼
   │   LoRA/QLoRA fine-tune a small open base (Qwen/Llama)  [offline, your GPU]
   │        │
   │        ▼
   ├── serve candidate on vLLM/Ollama → point SHADOW_MODEL_* at it
   │
   ├── shadow routing: candidate answers logged (role=shadow_candidate), NEVER served
   │
   └── eval.evaluate_shadow_capture()  ← candidate vs served reference, per task
            │  report.promotable()?
            ▼
      promote: set the task's model in task_registry (or OPEN_MODEL_BASE_URL) → done
```

## Pieces

| Module | Responsibility |
| --- | --- |
| [`capture.py`](capture.py) | `TrainingCapture` — writes PII-scrubbed, **consent-gated** `AiInteraction` rows (served + shadow); `record_feedback` labels them; `build_capture` wires it from settings. |
| [`shadow.py`](shadow.py) | `build_shadow_engine` — an OpenAI-compatible engine for the candidate model; `generate()` runs it ungated & log-only. |
| [`dataset.py`](dataset.py) | `export_task` (filters: consent, teacher-only, exclude-rejected) → training examples; `dataset_stats`. |
| [`eval.py`](eval.py) | `evaluate` / `evaluate_shadow_capture` — structured (JSON key/value) + freeform (token-Jaccard) scoring → `EvalReport.promotable()`. |

Data model: [`app/models/ai_interaction.py`](../models/ai_interaction.py)
(`ai_interaction` table). Lean cost telemetry (`escalated`, `confidence`) lives on
[`AiUsageLog`](../models/orchestrator_usage.py). Migration `d9e0f1a2b3c4`.

## How it hooks in (zero agent changes)

The `Orchestrator` accepts an optional `capture`. `get_orchestrator()` builds it
from settings, so once enabled it captures every served hosted/Claude result —
agents and services are untouched. Escalations (cheap tier → Claude) are flagged
as **hard examples**.

## Governance (built in, non-negotiable)

- **Consent:** nothing is captured unless `context["consent"] is True` **and**
  `ORCHESTRATOR_CAPTURE_TRAINING_DATA=true`. Both default off.
- **PII:** `prompt`/`system`/`output` are scrubbed (emails/phones) before storage
  (`pii_scrubbed=True`). A stricter NER pass is the documented next step.
- **Provenance:** every row records `engine_used`, `consented`, `role`. Before
  training on frontier outputs, confirm the provider's ToS permits it.
- **Model collapse:** always mix fresh teacher data + human/outcome labels; never
  train purely on the candidate's own output.

## Configuration

| setting | default | purpose |
| --- | --- | --- |
| `ORCHESTRATOR_CAPTURE_TRAINING_DATA` | `false` | master switch for capture |
| `ORCHESTRATOR_SHADOW_MODEL_ENABLED` | `false` | also log-only shadow candidate |
| `SHADOW_MODEL_PROVIDER` | `shadow` | label / keyless self-hosted |
| `SHADOW_MODEL_BASE_URL` | `None` | candidate endpoint (vLLM/Ollama) |
| `SHADOW_MODEL_API_KEY` | `None` | usually none (self-hosted) |
| `SHADOW_MODEL_NAME` | `embedhunt-distill-v0` | candidate model id |

## Tests

```bash
cd backend
python -m pytest tests/training/ -q
```
