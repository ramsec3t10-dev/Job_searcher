"""EMBEDHUNT AI — Knowledge Graph Repository.

Deterministic graph queries over the skill knowledge graph. Traversals load the
relevant edges once and walk the adjacency in Python (BFS), rather than matching
raw SQL strings, so prerequisite/learning-path answers follow the actual graph
structure.
"""
from collections import defaultdict, deque
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.base_repository import BaseRepository
from app.models.knowledge_graph import EdgeType, RoleRequirement, SkillEdge, SkillNode


class KnowledgeGraphRepository(BaseRepository[SkillNode]):
    def __init__(self, db: AsyncSession):
        super().__init__(db, SkillNode)

    async def get_by_name(self, name: str) -> Optional[SkillNode]:
        """Case-insensitive exact lookup of a single skill node."""
        r = await self.db.execute(
            select(SkillNode).where(func.lower(SkillNode.name) == (name or "").strip().lower())
        )
        return r.scalar_one_or_none()

    async def all_nodes(self) -> list[SkillNode]:
        r = await self.db.execute(select(SkillNode).order_by(SkillNode.name))
        return list(r.scalars().all())

    async def _adjacency(
        self, edge_type: EdgeType
    ) -> tuple[dict[str, set[str]], dict[str, set[str]], dict[str, SkillNode]]:
        """Load ``edge_type`` edges into forward/reverse adjacency + id→node map.

        ``forward[a]`` holds nodes ``b`` where ``a → b`` (a is a prerequisite of
        b); ``reverse[b]`` holds those same ``a`` (the prerequisites of b).
        """
        nodes = await self.all_nodes()
        nodes_by_id = {n.id: n for n in nodes}
        r = await self.db.execute(select(SkillEdge).where(SkillEdge.edge_type == edge_type))
        forward: dict[str, set[str]] = defaultdict(set)
        reverse: dict[str, set[str]] = defaultdict(set)
        for edge in r.scalars().all():
            forward[edge.from_skill_id].add(edge.to_skill_id)
            reverse[edge.to_skill_id].add(edge.from_skill_id)
        return forward, reverse, nodes_by_id

    async def get_prerequisites(self, skill_name: str) -> list[SkillNode]:
        """All transitive prerequisites of ``skill_name``, foundational-first.

        Walks ``PREREQUISITE_OF`` edges backward from the target and orders the
        result by distance (deepest/most foundational first), then name.
        """
        target = await self.get_by_name(skill_name)
        if target is None:
            return []
        _, reverse, nodes_by_id = await self._adjacency(EdgeType.PREREQUISITE_OF)
        depth: dict[str, int] = {}
        queue: deque[tuple[str, int]] = deque([(target.id, 0)])
        seen = {target.id}
        while queue:
            current, dist = queue.popleft()
            for prereq in reverse.get(current, set()):
                if prereq not in seen:
                    seen.add(prereq)
                    depth[prereq] = dist + 1
                    queue.append((prereq, dist + 1))
        ordered = sorted(depth.items(), key=lambda kv: (-kv[1], nodes_by_id[kv[0]].name))
        return [nodes_by_id[node_id] for node_id, _ in ordered]

    async def get_next_skills(self, skill_name: str) -> list[SkillNode]:
        """Direct successors of ``skill_name`` — what to learn *after* it.

        Returns the immediate ``PREREQUISITE_OF`` children, ordered by name.
        """
        node = await self.get_by_name(skill_name)
        if node is None:
            return []
        forward, _, nodes_by_id = await self._adjacency(EdgeType.PREREQUISITE_OF)
        successors = [nodes_by_id[i] for i in forward.get(node.id, set())]
        return sorted(successors, key=lambda n: n.name)

    async def get_learning_path(self, from_skill: str, to_skill: str) -> list[SkillNode]:
        """Shortest ``PREREQUISITE_OF`` path from ``from_skill`` to ``to_skill``.

        Returns the ordered nodes ``[from_skill, …, to_skill]``, or an empty list
        if either endpoint is unknown or no path exists. Neighbours are visited
        in name order so the chosen shortest path is deterministic.
        """
        start = await self.get_by_name(from_skill)
        end = await self.get_by_name(to_skill)
        if start is None or end is None:
            return []
        forward, _, nodes_by_id = await self._adjacency(EdgeType.PREREQUISITE_OF)
        if start.id == end.id:
            return [start]
        prev: dict[str, str] = {}
        queue: deque[str] = deque([start.id])
        seen = {start.id}
        while queue:
            current = queue.popleft()
            if current == end.id:
                break
            for nxt in sorted(forward.get(current, set()), key=lambda i: nodes_by_id[i].name):
                if nxt not in seen:
                    seen.add(nxt)
                    prev[nxt] = current
                    queue.append(nxt)
        if end.id not in seen:
            return []
        chain: list[str] = [end.id]
        while chain[-1] != start.id:
            chain.append(prev[chain[-1]])
        chain.reverse()
        return [nodes_by_id[node_id] for node_id in chain]

    async def get_role_requirements(self, role_name: str) -> list[SkillNode]:
        """Skills strictly required by ``role_name`` (required=True), by name."""
        r = await self.db.execute(
            select(SkillNode)
            .join(RoleRequirement, RoleRequirement.skill_id == SkillNode.id)
            .where(
                func.lower(RoleRequirement.role_name) == (role_name or "").strip().lower(),
                RoleRequirement.required == True,  # noqa: E712 — SQL boolean compare
            )
            .order_by(SkillNode.name)
        )
        return list(r.scalars().all())

    async def get_role_requirement_details(self, role_name: str) -> list[tuple[SkillNode, bool]]:
        """All skills mapped to ``role_name`` with their required flag.

        Required skills first, then recommended; alphabetical within each group.
        """
        r = await self.db.execute(
            select(SkillNode, RoleRequirement.required)
            .join(RoleRequirement, RoleRequirement.skill_id == SkillNode.id)
            .where(func.lower(RoleRequirement.role_name) == (role_name or "").strip().lower())
            .order_by(RoleRequirement.required.desc(), SkillNode.name)
        )
        return [(node, bool(required)) for node, required in r.all()]

    async def list_role_names(self) -> list[str]:
        r = await self.db.execute(
            select(RoleRequirement.role_name).distinct().order_by(RoleRequirement.role_name)
        )
        return list(r.scalars().all())
