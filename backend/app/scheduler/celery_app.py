"""EMBEDHUNT AI — Celery application & beat schedule.

Celery is an *optional* runtime dependency. When it is not installed this module
exposes a lightweight stand-in whose ``@task`` decorator returns the wrapped
function (augmented with a synchronous ``.delay``) and whose
``conf.beat_schedule`` is a plain dict — so the task module stays importable and
unit-testable without a broker.
"""
from __future__ import annotations

from app.config.settings import settings

CELERY_AVAILABLE = False

try:  # pragma: no cover - exercised only where celery is installed
    from celery import Celery

    celery_app = Celery(
        "embedhunt",
        broker=settings.CELERY_BROKER_URL,
        backend=settings.CELERY_RESULT_BACKEND,
    )
    celery_app.conf.timezone = "UTC"
    CELERY_AVAILABLE = True
except Exception:  # noqa: BLE001 — celery is optional
    class _Conf:
        def __init__(self) -> None:
            self.beat_schedule: dict = {}
            self.timezone = "UTC"

    class _StubCelery:
        """Minimal Celery stand-in used when the real package is absent."""

        def __init__(self, name: str) -> None:
            self.name = name
            self.conf = _Conf()

        def task(self, *dargs, **dkwargs):
            def wrap(fn):
                fn.delay = lambda *a, **k: fn(*a, **k)
                return fn

            if dargs and callable(dargs[0]):
                return wrap(dargs[0])
            return wrap

    celery_app = _StubCelery("embedhunt")
