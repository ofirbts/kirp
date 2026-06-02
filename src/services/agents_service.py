"""
Agents service — AgentFramework + AgentEngine.

List/get agents from registry; enqueue runs via AgentEngine.
"""

from __future__ import annotations

from typing import Any, List, Optional

from src.core.agent_registry import get_agent_framework_with_all_agents
from src.schemas.api_models import Agent


def _spec_to_agent(spec: Any, tenant_id: str, space_id: Optional[str] = None) -> Agent:
    return Agent(
        id=spec.name,
        name=spec.name,
        type=spec.type,
        status="idle",
        ownerUserId=None,
        description=spec.description or "",
        lastRunAt=None,
        tenantId=tenant_id,
        spaceId=space_id,
        connectedWorkflowIds=[],
        triggers=spec.triggers,
        config={"tools": spec.tools, "autonomy": spec.autonomy.value},
        metrics=[],
    )


async def list_agents(
    tenant_id: Optional[str] = None,
    space_id: Optional[str] = None,
    status: Optional[str] = None,
    agent_type: Optional[str] = None,
) -> List[Agent]:
    """List agents from framework (tenant-scoped by tenant_scopes)."""
    af = get_agent_framework_with_all_agents()
    specs = af.list_all()
    out = []
    for s in specs:
        if tenant_id and s.tenant_scopes and tenant_id not in s.tenant_scopes:
            continue
        if agent_type and s.type != agent_type:
            continue
        out.append(_spec_to_agent(s, tenant_id or "default", space_id))
    if status:
        out = [a for a in out if a.status == status]
    return out


async def get_agent(
    agent_id: str,
    tenant_id: Optional[str] = None,
    space_id: Optional[str] = None,
) -> Optional[Agent]:
    """Get single agent by id (name)."""
    af = get_agent_framework_with_all_agents()
    spec = af.get(agent_id)
    if not spec:
        return None
    if tenant_id and spec.tenant_scopes and tenant_id not in spec.tenant_scopes:
        return None
    return _spec_to_agent(spec, tenant_id or "default", space_id)
