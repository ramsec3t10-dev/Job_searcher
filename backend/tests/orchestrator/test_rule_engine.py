"""EMBEDHUNT AI — Rule engine tests.

Covers the two shipped handlers (daily_brief, flashcard_schedule), registration
of custom handlers, and the None-fallthrough for unregistered tasks.
"""
import json

from app.orchestrator.rule_engine import RuleEngine


async def test_daily_brief_renders_payload():
    engine = RuleEngine()
    result = await engine.run(
        "daily_brief",
        {"name": "Ada", "streak_days": 5, "new_matches": 3, "pending_applications": 2},
    )
    assert result is not None
    assert result.engine_used == "rule:daily_brief"
    assert result.cost_estimate_usd == 0.0
    assert result.confidence == 1.0
    assert result.cached is False
    assert "Ada" in result.text
    assert "5 days" in result.text
    assert "3" in result.text


async def test_daily_brief_singular_day():
    engine = RuleEngine()
    result = await engine.run("daily_brief", {"name": "Bo", "streak_days": 1})
    assert "1 day." in result.text  # singular, not "1 days"


async def test_flashcard_schedule_good_recall_advances():
    engine = RuleEngine()
    result = await engine.run(
        "flashcard_schedule",
        {"quality": 5, "repetitions": 2, "ease_factor": 2.5, "interval_days": 6},
    )
    data = json.loads(result.text)
    assert data["repetitions"] == 3
    assert data["interval_days"] == round(6 * 2.5)  # prev interval * ease
    assert data["ease_factor"] >= 2.5  # a perfect grade nudges ease up


async def test_flashcard_schedule_poor_recall_resets():
    engine = RuleEngine()
    result = await engine.run(
        "flashcard_schedule",
        {"quality": 1, "repetitions": 4, "ease_factor": 2.5, "interval_days": 30},
    )
    data = json.loads(result.text)
    assert data["repetitions"] == 0  # reset to the start of the ladder
    assert data["interval_days"] == 1  # review again tomorrow
    assert data["ease_factor"] >= 1.3  # never drops below the SM-2 floor


async def test_flashcard_schedule_first_review_ladder():
    engine = RuleEngine()
    first = await engine.run("flashcard_schedule", {"quality": 4, "repetitions": 0})
    second = await engine.run("flashcard_schedule", {"quality": 4, "repetitions": 1})
    assert json.loads(first.text)["interval_days"] == 1
    assert json.loads(second.text)["interval_days"] == 6


async def test_unregistered_task_returns_none():
    engine = RuleEngine()
    assert await engine.run("does_not_exist", {}) is None


async def test_register_custom_handler():
    engine = RuleEngine(register_defaults=False)
    assert engine.handles("daily_brief") is False

    engine.register("shout", lambda payload, ctx: payload["msg"].upper())
    result = await engine.run("shout", {"msg": "hi"})
    assert result.text == "HI"
    assert result.engine_used == "rule:shout"


async def test_unregister_handler():
    engine = RuleEngine()
    assert engine.handles("daily_brief") is True
    engine.unregister("daily_brief")
    assert engine.handles("daily_brief") is False
    assert await engine.run("daily_brief", {}) is None
