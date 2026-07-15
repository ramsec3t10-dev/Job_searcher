"""EMBEDHUNT AI — AI Orchestrator package.

A single routing layer over every inference backend. Services call
``Orchestrator.handle(task, payload, context)`` instead of hitting Bedrock
directly, and the orchestrator resolves each task through a fixed fallthrough
chain of pluggable engines:

    rule_engine → knowledge_graph_engine → cache_engine (exact match)
        → hosted_model_engine (Together AI, gated) → claude_engine

See ``app/orchestrator/README.md`` for the fallthrough contract and how to
register new rule handlers or task types.
"""
from app.orchestrator.cache_engine import CacheEngine
from app.orchestrator.claude_engine import ClaudeEngine
from app.orchestrator.engine_base import EngineResult, InferenceEngine
from app.orchestrator.gateway import OrchestratorGateway
from app.orchestrator.hosted_model_engine import HostedModelEngine, OpenModelEngine
from app.orchestrator.knowledge_graph_engine import KnowledgeGraphEngine
from app.orchestrator.router import Orchestrator, OrchestratorError
from app.orchestrator.rule_engine import RuleEngine

__all__ = [
    "Orchestrator",
    "OrchestratorError",
    "OrchestratorGateway",
    "InferenceEngine",
    "EngineResult",
    "RuleEngine",
    "KnowledgeGraphEngine",
    "CacheEngine",
    "HostedModelEngine",
    "OpenModelEngine",
    "ClaudeEngine",
]
