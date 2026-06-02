from __future__ import annotations

import pytest

from src.core.governance import GovernanceEngine


@pytest.mark.asyncio
async def test_governance_fail_closed_without_opa_in_production(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENV", "production")
    monkeypatch.setenv("KIRP_REQUIRE_OPA", "1")
    engine = GovernanceEngine(opa_url=None)
    check = await engine.check("t1", "all", "u1", "write", "event")
    assert check.allowed is False
    assert "OPA required" in check.reason


@pytest.mark.asyncio
async def test_governance_allow_without_opa_in_development(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENV", "development")
    engine = GovernanceEngine(opa_url=None)
    check = await engine.check("t1", "all", "u1", "write", "event")
    assert check.allowed is True


@pytest.mark.asyncio
async def test_update_by_external_id_appends_correction_event() -> None:
    from unittest.mock import AsyncMock, MagicMock
    from uuid import uuid4

    from src.core.event_store import Event, EventStore

    store = EventStore("mongodb://localhost:27017")
    store._db = MagicMock()
    existing_id = uuid4()
    existing = Event(
        id=existing_id,
        tenant_id="t1",
        space_id="all",
        user_id="u1",
        source="notion",
        content="old",
        metadata={"external_id": "ext-1"},
    )
    store.find_by_external_id = AsyncMock(return_value=existing)
    store._db.events.update_one = AsyncMock(return_value=MagicMock(modified_count=1))
    store.ingest = AsyncMock(return_value=existing_id)

    ok = await store.update_by_external_id("t1", "notion", "ext-1", "new content", {"external_id": "ext-1"})
    assert ok is True
    store.ingest.assert_awaited_once()
    correction = store.ingest.await_args[0][0]
    assert correction.event_type == "event.corrected"
    assert correction.parent_event_id == existing_id


@pytest.mark.asyncio
async def test_count_events_requires_tenant() -> None:
    from src.core.event_store import EventStore

    store = EventStore("mongodb://localhost:27017")
    with pytest.raises(ValueError, match="tenant_id is required"):
        await store.count_events("")
