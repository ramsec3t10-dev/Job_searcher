"""EMBEDHUNT AI — Knowledge Graph seed (idempotent).

Populates the skill knowledge graph with a realistic embedded-engineering
domain: the prescribed automotive learning chain

    CAN → RTOS → MCAL → BSW → AUTOSAR → Functional Safety (ISO 26262)

plus surrounding nodes/edges across the domains referenced in the resume schema
(programming, rtos_os, protocols, hardware, automotive, tools) and a few
role→skill requirement maps.

Idempotent: nodes are keyed by name, edges by (from, to, type) and role
requirements by (role, skill), so re-running never creates duplicates. Run it
directly against the configured database with::

    python -m database.seeds.knowledge_graph_seed
"""
from __future__ import annotations

import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge_graph import EdgeType, RoleRequirement, SkillEdge, SkillNode

# ── Nodes: (name, category) — categories mirror app/ai/skill_extractor taxonomy.
NODES: list[tuple[str, str]] = [
    ("Embedded C", "programming"),
    ("C++", "programming"),
    ("MISRA C", "concepts"),
    ("ARM Cortex-M", "hardware"),
    ("STM32", "hardware"),
    ("GPIO", "hardware"),
    ("UART", "protocols"),
    ("SPI", "protocols"),
    ("I2C", "protocols"),
    ("CAN", "protocols"),
    ("CAN FD", "protocols"),
    ("LIN", "protocols"),
    ("FlexRay", "protocols"),
    ("Automotive Ethernet", "protocols"),
    ("UDS", "protocols"),
    ("Bare-metal Firmware", "rtos_os"),
    ("FreeRTOS", "rtos_os"),
    ("RTOS", "rtos_os"),
    ("Embedded Linux", "rtos_os"),
    ("MCAL", "automotive"),
    ("RTE", "automotive"),
    ("BSW", "automotive"),
    ("AUTOSAR", "automotive"),
    ("Functional Safety (ISO 26262)", "automotive"),
    ("ASPICE", "automotive"),
    ("JTAG/SWD Debugging", "tools"),
    ("CANoe", "tools"),
    ("Oscilloscope & Logic Analyzer", "tools"),
]

# ── Edges: (from_name, to_name, edge_type). PREREQUISITE_OF reads "from is a
#    prerequisite of to" (learn from before to).
_P = EdgeType.PREREQUISITE_OF
_R = EdgeType.REQUIRED_BY
_C = EdgeType.COMMONLY_PAIRED_WITH

EDGES: list[tuple[str, str, EdgeType]] = [
    # Foundations & serial protocols
    ("Embedded C", "C++", _P),
    ("Embedded C", "GPIO", _P),
    ("GPIO", "UART", _P),
    ("UART", "SPI", _P),
    ("UART", "I2C", _P),
    ("UART", "CAN", _P),
    ("Embedded C", "CAN", _P),
    ("CAN", "CAN FD", _P),
    ("CAN", "LIN", _P),
    ("CAN", "FlexRay", _P),
    ("CAN", "UDS", _P),
    ("CAN FD", "Automotive Ethernet", _P),
    # Hardware & bare-metal → RTOS
    ("ARM Cortex-M", "STM32", _P),
    ("STM32", "Bare-metal Firmware", _P),
    ("Embedded C", "Bare-metal Firmware", _P),
    ("Bare-metal Firmware", "FreeRTOS", _P),
    ("FreeRTOS", "RTOS", _P),
    ("Embedded C", "Embedded Linux", _P),
    # Prescribed AUTOSAR chain: CAN → RTOS → MCAL → BSW → AUTOSAR → Safety
    ("CAN", "RTOS", _P),
    ("RTOS", "MCAL", _P),
    ("MCAL", "BSW", _P),
    ("MCAL", "RTE", _P),
    ("RTE", "AUTOSAR", _P),
    ("BSW", "AUTOSAR", _P),
    ("AUTOSAR", "Functional Safety (ISO 26262)", _P),
    # Hard requirements (required_by)
    ("MISRA C", "Functional Safety (ISO 26262)", _R),
    ("UDS", "AUTOSAR", _R),
    # Commonly paired (tooling / process companions)
    ("CAN", "CANoe", _C),
    ("AUTOSAR", "ASPICE", _C),
    ("Functional Safety (ISO 26262)", "MISRA C", _C),
    ("STM32", "JTAG/SWD Debugging", _C),
    ("SPI", "Oscilloscope & Logic Analyzer", _C),
]

# ── Role requirements: (role_name, skill_name, required)
ROLES: list[tuple[str, str, bool]] = [
    ("AUTOSAR Engineer", "AUTOSAR", True),
    ("AUTOSAR Engineer", "MCAL", True),
    ("AUTOSAR Engineer", "BSW", True),
    ("AUTOSAR Engineer", "RTE", True),
    ("AUTOSAR Engineer", "CAN", True),
    ("AUTOSAR Engineer", "Embedded C", True),
    ("AUTOSAR Engineer", "Functional Safety (ISO 26262)", False),
    ("AUTOSAR Engineer", "ASPICE", False),
    ("Embedded Firmware Engineer", "Embedded C", True),
    ("Embedded Firmware Engineer", "RTOS", True),
    ("Embedded Firmware Engineer", "FreeRTOS", True),
    ("Embedded Firmware Engineer", "ARM Cortex-M", True),
    ("Embedded Firmware Engineer", "SPI", True),
    ("Embedded Firmware Engineer", "I2C", True),
    ("Embedded Firmware Engineer", "UART", True),
    ("Embedded Firmware Engineer", "JTAG/SWD Debugging", False),
    ("Functional Safety Engineer", "Functional Safety (ISO 26262)", True),
    ("Functional Safety Engineer", "MISRA C", True),
    ("Functional Safety Engineer", "Embedded C", True),
    ("Functional Safety Engineer", "AUTOSAR", False),
    ("Functional Safety Engineer", "ASPICE", False),
]


async def seed_knowledge_graph(session: AsyncSession) -> dict[str, int]:
    """Seed nodes, edges and role requirements. Safe to run repeatedly.

    Returns a dict of created/total counts for reporting.
    """
    # Nodes — keyed by name.
    existing_nodes = {n.name: n for n in (await session.execute(select(SkillNode))).scalars().all()}
    nodes_created = 0
    for name, category in NODES:
        if name not in existing_nodes:
            node = SkillNode(name=name, category=category)
            session.add(node)
            existing_nodes[name] = node
            nodes_created += 1
    await session.flush()  # assign ids to any freshly-added nodes
    name_to_id = {name: node.id for name, node in existing_nodes.items()}

    # Edges — keyed by (from_id, to_id, edge_type).
    existing_edges = {
        (e.from_skill_id, e.to_skill_id, e.edge_type)
        for e in (await session.execute(select(SkillEdge))).scalars().all()
    }
    edges_created = 0
    for from_name, to_name, edge_type in EDGES:
        key = (name_to_id[from_name], name_to_id[to_name], edge_type)
        if key not in existing_edges:
            session.add(SkillEdge(from_skill_id=key[0], to_skill_id=key[1], edge_type=edge_type))
            existing_edges.add(key)
            edges_created += 1

    # Role requirements — keyed by (role_name, skill_id).
    existing_roles = {
        (rr.role_name, rr.skill_id)
        for rr in (await session.execute(select(RoleRequirement))).scalars().all()
    }
    roles_created = 0
    for role_name, skill_name, required in ROLES:
        key = (role_name, name_to_id[skill_name])
        if key not in existing_roles:
            session.add(RoleRequirement(role_name=role_name, skill_id=key[1], required=required))
            existing_roles.add(key)
            roles_created += 1

    await session.flush()
    return {
        "nodes_created": nodes_created,
        "edges_created": edges_created,
        "roles_created": roles_created,
        "nodes_total": len(NODES),
        "edges_total": len(EDGES),
        "roles_total": len(ROLES),
    }


async def _main() -> None:
    from app.database.session import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        counts = await seed_knowledge_graph(session)
        await session.commit()
    print(
        "knowledge_graph seed complete: "
        f"nodes +{counts['nodes_created']}/{counts['nodes_total']}, "
        f"edges +{counts['edges_created']}/{counts['edges_total']}, "
        f"roles +{counts['roles_created']}/{counts['roles_total']}"
    )


if __name__ == "__main__":
    asyncio.run(_main())
