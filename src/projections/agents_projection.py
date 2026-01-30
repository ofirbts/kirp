"""
Agent projections.

Translate agent definitions and runtime metadata into `Agent` projection
rows in Postgres. These projections are used by the frontend for listing
and inspecting agents, not as the source of truth for behaviour.
"""

from __future__ import annotations

from typing import Any, Mapping, Optional
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import Agent


async def upsert_agent(
    session: AsyncSession,
    *,
    agent_id: Optional[UUID] = None,
    name: str,
    type: str,
    status: str,
    tenant_id: str,
    space_id: Optional[str] = None,
    owner_user_id: Optional[str] = None,
    description: Optional[str] = None,
    connected_workflow_ids: Optional[list[UUID]] = None,
    triggers: Optional[list[str]] = None,
    config: Optional[Mapping[str, Any]] = None,
    metrics: Optional[list[dict[str, Any]]] = None,
    last_run_at: Optional[str] = None,
) -> Agent:
    """
    Insert or update an Agent projection.

    - `agent_id` is the UUID of the agent in the event store / domain model.
    - All list-like fields (connected_workflow_ids, triggers, metrics) are
      stored as ARRAY/JSON.
    """
    agent_pk = agent_id or uuid4()

    stmt = select(Agent).where(Agent.id == agent_pk, Agent.tenant_id == tenant_id)
    result = await session.execute(stmt)
    existing: Optional[Agent] = result.scalar_one_or_none()

    if existing:
        existing.name = name
        existing.type = type
        existing.status = status
        existing.owner_user_id = owner_user_id
        existing.description = description
        existing.tenant_id = tenant_id
        existing.space_id = space_id
        existing.connected_workflow_ids = list(connected_workflow_ids or [])
        existing.triggers = list(triggers or [])
        existing.config = dict(config or {})
        existing.metrics = list(metrics or [])
        existing.last_run_at = last_run_at
        await session.flush()
        return existing

    agent = Agent(
        id=agent_pk,
        name=name,
        type=type,
        status=status,
        owner_user_id=owner_user_id,
        tenant_id=tenant_id,
        space_id=space_id,
        description=description,
        connected_workflow_ids=list(connected_workflow_ids or []),
        triggers=list(triggers or []),
        config=dict(config or {}),
        metrics=list(metrics or []),
        last_run_at=last_run_at,
    )
    session.add(agent)
    await session.flush()
    return agent

