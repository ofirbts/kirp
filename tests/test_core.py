"""
Basic core tests — Event, EventStore, RAGEngine, AgentFramework, Governance.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from uuid import uuid4

import pytest

from src.core.event_store import Event, EventStore, Sensitivity
from src.core.agent_framework import AgentFramework, AgentSpec, AutonomyLevel
from src.core.governance import GovernanceEngine, GovernanceCheck


def test_event_to_doc_roundtrip() -> None:
    ev = Event(
        id=uuid4(),
        tenant_id="t1",
        space_id="s1",
        user_id="u1",
        source="test",
        content="hello",
        metadata={"k": "v"},
        embedding=[],
        timestamp=datetime.now(timezone.utc),
        sensitivity=Sensitivity.PRIVATE,
        event_type="ingest",
    )
    doc = ev.to_doc()
    assert doc["tenant_id"] == "t1"
    assert doc["user_id"] == "u1"
    ev2 = Event.from_doc(doc)
    assert ev2.tenant_id == ev.tenant_id
    assert ev2.content == ev.content


def test_agent_framework_register_list() -> None:
    af = AgentFramework()
    spec = AgentSpec(
        name="TestAgent",
        type="test",
        triggers=["ingest"],
        tools=[],
        autonomy=AutonomyLevel.FULL,
        tenant_scopes=[],
    )
    af.register(spec)
    assert af.get("TestAgent") is spec
    assert len(af.list_by_trigger("ingest")) == 1
    assert len(af.list_all()) == 1


def test_governance_disabled() -> None:
    async def _check() -> GovernanceCheck:
        gov = GovernanceEngine(opa_url="")  # disabled when no OPA URL
        return await gov.check("t1", "s1", "u1", "read", "event")

    check = asyncio.run(_check())
    assert check.allowed is True
    assert "disabled" in check.reason.lower() or "opa" in check.reason.lower() or "no opa" in check.reason.lower()
