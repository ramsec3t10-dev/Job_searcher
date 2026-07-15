"""EMBEDHUNT AI — Training capture & distillation pipeline (Phase 5).

Turns the orchestrator's live traffic into a training substrate for EMBEDHUNT's
own future models:

* ``capture`` — writes PII-scrubbed, consent-gated input/output pairs to
  ``ai_interaction`` (served answers, plus log-only *shadow* candidate answers).
* ``dataset`` — exports captured pairs as fine-tuning-ready examples.
* ``eval`` — scores a candidate model's answers against the served references,
  per task (the distillation quality gate).
* ``shadow`` — builds the candidate-model engine used for log-only shadow runs.

Nothing here serves a candidate model to users — promotion happens only by
pointing the orchestrator's routing at a model once it clears the eval bar.
"""
from app.training.capture import TrainingCapture, build_capture, record_feedback

__all__ = ["TrainingCapture", "build_capture", "record_feedback"]
