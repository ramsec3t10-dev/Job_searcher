"""EMBEDHUNT AI — confidence-heuristic escalation eval (Phase 6).

Runs the labeled set through the **real orchestrator** (open-model engine with a
stubbed provider call + a mocked Claude) and reports how often the Phase-3
confidence heuristic's escalate/serve decision matched independent quality
judgement. This is a v1 sanity check that the heuristic isn't wildly over- or
under-escalating — not a precision benchmark.

Run with output:  pytest tests/orchestrator/eval/ -s
"""
from unittest.mock import AsyncMock, MagicMock

from app.orchestrator.cache_engine import CacheEngine
from app.orchestrator.claude_engine import ClaudeEngine
from app.orchestrator.engine_base import EngineResult
from app.orchestrator.hosted_model_engine import HostedModelEngine
from app.orchestrator.knowledge_graph_engine import KnowledgeGraphEngine
from app.orchestrator.router import Orchestrator
from app.orchestrator.rule_engine import RuleEngine

from tests.orchestrator.eval.labeled_set import LABELED

# Sanity gates for v1 (not a precision target — just "not wildly off").
_MIN_ACCURACY = 0.80
_MAX_OVER_ESCALATION_RATE = 0.15  # serving-quality answers wrongly sent to Claude = wasted $


def _build_orchestrator():
    """Real hosted engine (provider call stubbed) + mocked Claude; cache off."""
    hosted = HostedModelEngine(api_key="test-key")

    holder = {"content": "", "finish_reason": "stop"}

    async def fake_chat(messages, model, max_tokens=None):
        return {"content": holder["content"], "tokens_in": 50, "tokens_out": 20,
                "finish_reason": holder["finish_reason"]}

    hosted._chat_completion = fake_chat  # type: ignore[method-assign]

    kg = MagicMock(spec=KnowledgeGraphEngine)
    kg.run = AsyncMock(return_value=None)
    claude = MagicMock(spec=ClaudeEngine)
    claude.run = AsyncMock(return_value=EngineResult(text="[claude fallback]", engine_used="claude:mock"))

    orch = Orchestrator(
        rule_engine=RuleEngine(), knowledge_graph_engine=kg,
        cache_engine=CacheEngine(force_memory=True), hosted_model_engine=hosted, claude_engine=claude,
    )
    orch._cache_enabled = False  # avoid cross-example cache/semantic bleed
    return orch, holder


async def _run_eval() -> dict:
    orch, holder = _build_orchestrator()
    rows = []
    for i, ex in enumerate(LABELED):
        holder["content"] = ex["output"]
        holder["finish_reason"] = ex["finish_reason"]
        result = await orch.handle(ex["task"], {"prompt": f"[{i}] {ex['task']} input"})
        escalated = result.engine_used.startswith("claude")
        rows.append({**ex, "escalated": escalated, "match": escalated == ex["expect_escalate"]})

    n = len(rows)
    correct = sum(r["match"] for r in rows)
    over = [r for r in rows if r["escalated"] and not r["expect_escalate"]]   # served-worthy → Claude
    under = [r for r in rows if not r["escalated"] and r["expect_escalate"]]  # bad answer served
    return {
        "n": n,
        "accuracy": round(correct / n, 3),
        "over_escalation_rate": round(len(over) / n, 3),
        "under_escalation_rate": round(len(under) / n, 3),
        "over": over,
        "under": under,
    }


def _print_report(report: dict) -> None:
    print("\n" + "=" * 68)
    print("CONFIDENCE-HEURISTIC ESCALATION EVAL")
    print("=" * 68)
    print(f"examples            : {report['n']}")
    print(f"accuracy            : {report['accuracy']:.1%}  (heuristic agrees with quality judgement)")
    print(f"over-escalation     : {report['over_escalation_rate']:.1%}  (good answers sent to Claude — wasted $)")
    print(f"under-escalation    : {report['under_escalation_rate']:.1%}  (weak answers served instead of escalated)")
    if report["under"]:
        print("\nunder-escalations (heuristic served, quality judgement wanted Claude):")
        for r in report["under"]:
            print(f"  - {r['task']:26} {r['note']}")
    if report["over"]:
        print("\nover-escalations (heuristic escalated, answer was serve-worthy):")
        for r in report["over"]:
            print(f"  - {r['task']:26} {r['note']}")
    print("=" * 68)


async def test_confidence_heuristic_escalation():
    report = await _run_eval()
    _print_report(report)
    assert report["n"] >= 20, "need a meaningful labeled set"
    assert report["accuracy"] >= _MIN_ACCURACY, f"heuristic accuracy {report['accuracy']} below {_MIN_ACCURACY}"
    # The costly failure mode to guard against is over-escalating (paying Claude
    # for answers the cheap model handled fine).
    assert report["over_escalation_rate"] <= _MAX_OVER_ESCALATION_RATE
