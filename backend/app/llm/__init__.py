"""EMBEDHUNT AI — LLM foundation package.

A model-agnostic AI layer over AWS Bedrock (Anthropic): task-based model
routing, semantic caching, cost tracking, guardrails, token budgeting and
conversation management behind a single AIRouter entry point.
"""
from app.llm.bedrock_client import BedrockClient
from app.llm.cache import SemanticCache
from app.llm.cost_tracker import CostTracker
from app.llm.model_selector import TaskType
from app.llm.router import AIResponse, AIRouter

__all__ = ["AIRouter", "AIResponse", "TaskType", "BedrockClient", "CostTracker", "SemanticCache"]
