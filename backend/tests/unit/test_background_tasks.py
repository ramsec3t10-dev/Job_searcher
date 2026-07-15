"""Unit tests — Scheduled AI tasks (Part E).

The DB session, user-lookup helpers and service classes are patched so each
Celery task can be driven synchronously and asserted to call the right service.
"""
from app.scheduler import ai_tasks


class _FakeSession:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def commit(self):
        pass


def _fake_session_factory():
    return _FakeSession()


def _users(*names):
    async def _get(session):
        return list(names)

    return _get


def test_daily_twin_recompute_calls_service(monkeypatch):
    calls = []

    class FakeTwinService:
        def __init__(self, session):
            pass

        async def recompute_scores(self, user_id):
            calls.append(user_id)

    monkeypatch.setattr(ai_tasks, "AsyncSessionLocal", _fake_session_factory)
    monkeypatch.setattr(ai_tasks, "get_active_users_last_7_days", _users("u1", "u2"))
    monkeypatch.setattr(ai_tasks, "CareerTwinService", FakeTwinService)

    result = ai_tasks.daily_twin_recompute()
    assert result == 2
    assert calls == ["u1", "u2"]


def test_weekly_memory_cleanup_summarizes_and_prunes(monkeypatch):
    summarized = []
    pruned = {"count": 0}

    class FakeMemoryRepo:
        def __init__(self, session, router=None):
            pass

        async def summarize_old(self, user_id):
            summarized.append(user_id)

        async def delete_expired(self):
            pruned["count"] += 1

    monkeypatch.setattr(ai_tasks, "AsyncSessionLocal", _fake_session_factory)
    monkeypatch.setattr(ai_tasks, "get_all_users", _users("u1", "u2", "u3"))
    monkeypatch.setattr(ai_tasks, "MemoryRepository", FakeMemoryRepo)

    result = ai_tasks.weekly_memory_cleanup()
    assert result == 3
    assert summarized == ["u1", "u2", "u3"]
    assert pruned["count"] == 1


def test_daily_review_notifications_only_when_queue(monkeypatch):
    notified = []

    class FakeAdaptive:
        def __init__(self, session):
            pass

        async def get_review_queue(self, user_id):
            return ["can", "spi"] if user_id == "u1" else []

    class FakeNotifications:
        def __init__(self, session):
            pass

        async def create_review_reminder(self, user_id, skill_count):
            notified.append((user_id, skill_count))

    monkeypatch.setattr(ai_tasks, "AsyncSessionLocal", _fake_session_factory)
    monkeypatch.setattr(ai_tasks, "get_active_users_last_7_days", _users("u1", "u2"))
    monkeypatch.setattr(ai_tasks, "AdaptiveLearningService", FakeAdaptive)
    monkeypatch.setattr(ai_tasks, "NotificationService", FakeNotifications)

    result = ai_tasks.daily_review_notifications()
    assert result == 1
    assert notified == [("u1", 2)]
