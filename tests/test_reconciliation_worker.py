"""Partial-run reconciliation (history replay + RunController state)."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest

import src.core.run_controller as rcmod
from src.core.event_store import Event, Sensitivity
from src.core.pipeline import EventPipeline


@pytest.fixture
def run_id_fixture() -> str:
    return "run_75c5752911fa4a6db5057f5664eb572f"


@pytest.fixture
def seeded_partial_run(monkeypatch: pytest.MonkeyPatch, run_id_fixture: str) -> str:
    async def _seed() -> str:
        c = rcmod.RunController(redis_ping_max_attempts=1)

        async def _no_redis(self: rcmod.RunController) -> object:
            return None

        monkeypatch.setattr(rcmod.RunController, "_redis_client", _no_redis)
        monkeypatch.setattr(rcmod, "_run_controller", c)

        rid = run_id_fixture
        await c.create_run("ingest", "default", trace_id="tr_recon", run_id=rid)
        await c.update_step(rid, "mongo_write", "completed")
        await c.update_step(rid, "qdrant_projection", "completed")
        await c.update_step(rid, "history_write_failed", "failed", error="connection refused")
        await c.update_step(rid, "schema_projection", "completed")
        await c.update_step(rid, "pipeline_start", "completed")
        await c.update_step(rid, "pipeline_complete", "completed")
        st = await c.get_run_state(rid)
        assert st is not None
        assert st.state == "partial"
        return rid

    return asyncio.run(_seed())


@pytest.fixture
def fake_event(run_id_fixture: str) -> Event:
    return Event(
        id=uuid4(),
        tenant_id="default",
        space_id="default",
        user_id="u1",
        source="api",
        content="reconcile me",
        metadata={"run_id": run_id_fixture, "trace_id": "tr_recon"},
        embedding=[],
        timestamp=datetime.now(timezone.utc),
        sensitivity=Sensitivity.PRIVATE,
    )


@pytest.fixture
def pipeline_with_fakes(monkeypatch: pytest.MonkeyPatch, fake_event: Event, run_id_fixture: str) -> EventPipeline:
    class FakeStore:
        async def find_latest_by_run_id(self, tenant_id: str, run_id: str) -> Event | None:
            if tenant_id == "default" and run_id == run_id_fixture:
                return fake_event
            return None

    class FakeRAG:
        async def connect(self) -> None:
            return None

        async def embed(self, *_a: object, **_kw: object) -> list[float]:
            return []

        async def upsert(self, *_a: object, **_kw: object) -> None:
            return None

    class FakeSchema:
        async def connect(self) -> None:
            return None

        async def ensure_life_areas(self, *_a: object, **_kw: object) -> None:
            return None

        async def upsert_node(self, *_a: object, **_kw: object) -> None:
            return None

    class FakeGov:
        async def check(self, *_a: object, **_kw: object) -> SimpleNamespace:
            return SimpleNamespace(allowed=True, requires_approval=False, reason="ok")

    class FakeAgents:
        pass

    async def fake_record_history(**_kw: object) -> str:
        return "hist-entry-1"

    monkeypatch.setattr("src.core.history.record_history", fake_record_history)

    return EventPipeline(FakeStore(), FakeRAG(), FakeSchema(), FakeGov(), FakeAgents())


def test_reconcile_run_heals_history_and_completes_state(
    monkeypatch: pytest.MonkeyPatch,
    seeded_partial_run: str,
    pipeline_with_fakes: EventPipeline,
    run_id_fixture: str,
) -> None:
    async def _run() -> None:
        before = await rcmod.get_run_controller().get_run_status(run_id_fixture)
        assert before is not None
        assert before["state"] == "partial"
        last_hist = EventPipeline._last_step_status_map(before["steps"])
        assert last_hist.get("history_write_failed") == "failed"

        out = await pipeline_with_fakes.reconcile_run(run_id_fixture)
        assert out.get("skipped") is False
        assert "history" in out.get("repaired", [])

        after = await rcmod.get_run_controller().get_run_status(run_id_fixture)
        assert after is not None
        assert after["state"] == "completed"
        last_after = EventPipeline._last_step_status_map(after["steps"])
        assert last_after.get("history_write") == "completed"
        assert last_after.get("history_write_failed") == "completed"
        assert last_after.get("reconciled") == "completed"

    asyncio.run(_run())


def test_list_run_ids_by_state_partial(monkeypatch: pytest.MonkeyPatch) -> None:
    """Uses a fresh run_id so it stays independent of reconcile tests."""

    async def _run() -> None:
        rid = "run_list_partial_isolated"
        c = rcmod.RunController(redis_ping_max_attempts=1)

        async def _no_redis(self: rcmod.RunController) -> object:
            return None

        monkeypatch.setattr(rcmod.RunController, "_redis_client", _no_redis)
        monkeypatch.setattr(rcmod, "_run_controller", c)

        await c.create_run("ingest", "default", trace_id="tr_l", run_id=rid)
        await c.update_step(rid, "mongo_write", "completed")
        await c.update_step(rid, "qdrant_projection", "completed")
        await c.update_step(rid, "history_write_failed", "failed", error="x")
        await c.update_step(rid, "schema_projection", "completed")
        await c.update_step(rid, "pipeline_start", "completed")
        await c.update_step(rid, "pipeline_complete", "completed")
        assert (await c.get_run_state(rid)).state == "partial"

        ids = await c.list_run_ids_by_state("partial", limit=50)
        assert rid in ids

    asyncio.run(_run())
