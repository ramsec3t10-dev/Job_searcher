"""EMBEDHUNT AI — Knowledge Graph inference engine.

A deterministic, zero-LLM engine that answers skill-prerequisite,
learning-path and role-requirement questions by traversing the skill knowledge
graph. Skill/role names are found in the payload by simple keyword/entity match
against the known ``SkillNode`` names (no LLM); the graph is then traversed via
:class:`KnowledgeGraphRepository`.

Contract (per Phase 2 spec): for a supported task it returns an
:class:`EngineResult` with ``confidence=1.0`` when it fully resolves the query,
or ``confidence=None`` when the query does not match known nodes — the latter
tells the Orchestrator to keep falling through (cache → … → Claude). For any
unsupported task it returns ``None``.
"""
from __future__ import annotations

import re
from typing import Optional

from app.config.logging import get_logger
from app.orchestrator.engine_base import EngineResult, InferenceEngine
from app.repositories.knowledge_graph_repository import KnowledgeGraphRepository

logger = get_logger(__name__)

_SUPPORTED_TASKS = ("skill_query", "learning_path")

# Short skill names that collide with common English words; only matched when
# they appear in their exact (upper) case in the raw query (e.g. the "CAN" bus,
# not the modal "can").
_AMBIGUOUS_NAMES = {"c", "can", "go", "r"}

_NEXT_KEYWORDS = ("after", "next", "following", "then learn", "unlock", "beyond", "come after")


class KnowledgeGraphEngine(InferenceEngine):
    """Graph-backed engine for ``skill_query`` and ``learning_path`` tasks.

    A session is resolved per request from ``context["db"]`` when provided,
    otherwise from an injected ``session_factory`` (defaulting to the app's
    ``AsyncSessionLocal``). With no session available the engine falls through.
    """

    def __init__(self, session_factory=None):
        self._session_factory = session_factory

    # ── session plumbing ────────────────────────────────────────────────────
    @staticmethod
    def _default_factory():
        try:
            from app.database.session import AsyncSessionLocal

            return AsyncSessionLocal
        except Exception:  # noqa: BLE001 — DB layer optional at construction time
            return None

    async def run(
        self, task: str, payload: dict, context: Optional[dict] = None
    ) -> Optional[EngineResult]:
        if task not in _SUPPORTED_TASKS:
            return None
        context = context or {}
        session = context.get("db")
        if session is not None:
            return await self._answer(task, payload, session)
        factory = self._session_factory or self._default_factory()
        if factory is None:
            return None
        async with factory() as session:
            return await self._answer(task, payload, session)

    # ── answer routing ──────────────────────────────────────────────────────
    async def _answer(self, task: str, payload: dict, session) -> EngineResult:
        repo = KnowledgeGraphRepository(session)
        raw_query = str(payload.get("query", "") or "")
        query = raw_query.lower()
        node_names = [n.name for n in await repo.all_nodes()]
        alias_map = self._alias_map(node_names)

        if task == "learning_path":
            return await self._answer_learning_path(repo, payload, query, raw_query, alias_map)

        # task == "skill_query" — role / prerequisites / next-skills.
        role_names = await repo.list_role_names()
        role = payload.get("role") or self._match_role(query, role_names)
        matches = self._ordered_matches(query, raw_query, alias_map)
        explicit_skill = payload.get("skill")
        if explicit_skill:
            matches = [explicit_skill, *matches]

        intent = payload.get("intent")
        # Role requirements take precedence when a role phrase is present.
        if role and intent != "prerequisites" and intent != "next":
            return await self._answer_role(repo, role)

        if not matches:
            return self._fallthrough("no known skill in query")

        subject = max(matches, key=len)  # most specific matched skill name
        if intent == "next" or (intent != "prerequisites" and self._wants_next(query)):
            return await self._answer_next(repo, subject)
        return await self._answer_prerequisites(repo, subject)

    async def _answer_prerequisites(self, repo, skill: str) -> EngineResult:
        prereqs = await repo.get_prerequisites(skill)
        if prereqs:
            chain = " → ".join(n.name for n in prereqs)
            text = (
                f"To learn {skill}, build these up first "
                f"(foundational → advanced): {chain}."
            )
        else:
            text = f"{skill} has no prerequisites in the graph — it's a solid starting point."
        return self._hit(text, "prerequisites", skill)

    async def _answer_next(self, repo, skill: str) -> EngineResult:
        nxt = await repo.get_next_skills(skill)
        if nxt:
            text = f"After {skill}, the natural next step(s): " + ", ".join(n.name for n in nxt) + "."
        else:
            text = f"{skill} is a leaf in the graph — nothing listed to learn after it yet."
        return self._hit(text, "next_skills", skill)

    async def _answer_role(self, repo, role: str) -> EngineResult:
        details = await repo.get_role_requirement_details(role)
        if not details:
            return self._fallthrough(f"unknown role '{role}'")
        required = [n.name for n, req in details if req]
        recommended = [n.name for n, req in details if not req]
        lines = [f"Role '{role}' skill requirements:"]
        if required:
            lines.append("  Required: " + ", ".join(required))
        if recommended:
            lines.append("  Recommended: " + ", ".join(recommended))
        return self._hit("\n".join(lines), "role_requirements", role)

    async def _answer_learning_path(
        self, repo, payload: dict, query: str, raw_query: str, alias_map: dict
    ) -> EngineResult:
        from_skill = payload.get("from_skill")
        to_skill = payload.get("to_skill")
        if not (from_skill and to_skill):
            ordered = self._ordered_matches(query, raw_query, alias_map)
            if len(ordered) < 2:
                return self._fallthrough("need two known skills for a learning path")
            from_skill, to_skill = ordered[0], ordered[-1]

        start = await repo.get_by_name(from_skill)
        end = await repo.get_by_name(to_skill)
        if start is None or end is None:
            return self._fallthrough("learning-path endpoint not in graph")

        path = await repo.get_learning_path(start.name, end.name)
        if len(path) >= 2:
            chain = " → ".join(n.name for n in path)
            steps = len(path) - 1
            text = f"Learning path from {start.name} to {end.name}: {chain} ({steps} step(s))."
        elif len(path) == 1:
            text = f"{start.name} is already the target — no steps needed."
        else:
            text = f"No learning path from {start.name} to {end.name} exists in the graph."
        return self._hit(text, "learning_path", f"{start.name}->{end.name}")

    # ── result helpers ──────────────────────────────────────────────────────
    def _hit(self, text: str, intent: str, subject: str) -> EngineResult:
        logger.info("orchestrator_knowledge_graph", intent=intent, subject=subject)
        return EngineResult(
            text=text,
            engine_used="knowledge_graph",
            confidence=1.0,
            cached=False,
            cost_estimate_usd=0.0,
        )

    def _fallthrough(self, reason: str) -> EngineResult:
        # confidence=None signals the Orchestrator to keep falling through.
        logger.info("orchestrator_knowledge_graph_fallthrough", reason=reason)
        return EngineResult(
            text="",
            engine_used="knowledge_graph",
            confidence=None,
            cached=False,
            cost_estimate_usd=0.0,
        )

    # ── entity matching (keyword, no LLM) ───────────────────────────────────
    @staticmethod
    def _alias_map(names: list[str]) -> dict[str, str]:
        """Map lowercase alias → canonical node name.

        Adds the full name plus, for names like ``Functional Safety (ISO 26262)``,
        the prefix (``functional safety``) and the parenthesised part
        (``iso 26262``) so natural phrasings still resolve.
        """
        aliases: dict[str, str] = {}
        for name in names:
            aliases.setdefault(name.lower(), name)
            m = re.match(r"^(.*?)\s*\((.*?)\)\s*$", name)
            if m:
                if m.group(1):
                    aliases.setdefault(m.group(1).strip().lower(), name)
                if m.group(2):
                    aliases.setdefault(m.group(2).strip().lower(), name)
        return aliases

    @classmethod
    def _ordered_matches(cls, query: str, raw_query: str, alias_map: dict) -> list[str]:
        """Canonical node names present in the query, in order of appearance."""
        hits: list[tuple[int, int, str]] = []
        for alias, canonical in alias_map.items():
            pattern = r"(?<!\w)" + re.escape(alias) + r"(?!\w)"
            for m in re.finditer(pattern, query):
                if alias in _AMBIGUOUS_NAMES and not cls._ambiguous_ok(alias, canonical, raw_query):
                    continue
                hits.append((m.start(), len(alias), canonical))
        hits.sort(key=lambda h: (h[0], -h[1]))
        ordered: list[str] = []
        seen: set[str] = set()
        for _, _, canonical in hits:
            if canonical not in seen:
                seen.add(canonical)
                ordered.append(canonical)
        return ordered

    @staticmethod
    def _ambiguous_ok(alias: str, canonical: str, raw_query: str) -> bool:
        """Accept an ambiguous short alias only if it appears cased in the raw query."""
        for token in {canonical, alias.upper()}:
            if re.search(r"(?<!\w)" + re.escape(token) + r"(?!\w)", raw_query):
                return True
        return False

    @staticmethod
    def _match_role(query: str, role_names: list[str]) -> Optional[str]:
        """Return the first role whose full name appears in the query, if any."""
        for role in role_names:
            if role.lower() in query:
                return role
        return None

    @staticmethod
    def _wants_next(query: str) -> bool:
        return any(keyword in query for keyword in _NEXT_KEYWORDS)
