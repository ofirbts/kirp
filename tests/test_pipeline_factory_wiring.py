"""Ensure handlers/workers obtain EventPipeline via pipeline_factory (no duplicate wiring)."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.models.event import CanonicalEvent
from src.modules.m3.events import EVENT_M3_DAILY_REFLECTION_SUBMITTED


@pytest.fixture
def fake_pipeline() -> MagicMock:
    p = MagicMock()
    p.run = AsyncMock(return_value=uuid4())
    return p


def test_handle_ingest_v1_uses_create_connected_event_pipeline(
    monkeypatch: pytest.MonkeyPatch, fake_pipeline: MagicMock
) -> None:
    factory = AsyncMock(return_value=fake_pipeline)
    monkeypatch.setattr(
        "src.core.pipeline_factory.create_connected_event_pipeline",
        factory,
    )
    from src.core import event_registry_handlers as erh

    ev = CanonicalEvent(
        tenant_id="t1",
        space_id="s1",
        user_id="u1",
        source="kafka",
        content="hello",
        metadata={"k": "v"},
    )

    async def _run() -> None:
        await erh.handle_ingest_v1(ev)

    asyncio.run(_run())
    factory.assert_awaited_once()
    fake_pipeline.run.assert_awaited_once()


def test_handle_m3_event_uses_create_connected_event_pipeline(
    monkeypatch: pytest.MonkeyPatch, fake_pipeline: MagicMock
) -> None:
    factory = AsyncMock(return_value=fake_pipeline)
    monkeypatch.setattr(
        "src.core.pipeline_factory.create_connected_event_pipeline",
        factory,
    )
    monkeypatch.setattr(
        "src.modules.m3.writeback.m3_memory_writeback",
        AsyncMock(),
    )
    from src.modules.m3 import handlers as m3h

    ev = CanonicalEvent(
        tenant_id="t1",
        space_id="s1",
        user_id="u1",
        source="m3",
        event_type=EVENT_M3_DAILY_REFLECTION_SUBMITTED,
        content="reflect",
        metadata={"module": "m3"},
    )

    async def _run() -> None:
        await m3h.handle_m3_event(ev)

    asyncio.run(_run())
    factory.assert_awaited_once()
    fake_pipeline.run.assert_awaited_once()


def test_reconciliation_worker_create_uses_factory(
    monkeypatch: pytest.MonkeyPatch, fake_pipeline: MagicMock
) -> None:
    factory = AsyncMock(return_value=fake_pipeline)
    monkeypatch.setattr(
        "src.core.pipeline_factory.create_connected_event_pipeline",
        factory,
    )
    from src.workers.reconciliation_worker import ReconciliationWorker

    async def _run() -> ReconciliationWorker:
        return await ReconciliationWorker.create()

    w = asyncio.run(_run())
    factory.assert_awaited_once()
    assert w._pipeline is fake_pipeline
