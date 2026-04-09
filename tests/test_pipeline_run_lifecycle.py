"""EventPipeline.run: Phase 1 visibility + Phase 2 PIPELINE_RUN_POLICY strict."""

from __future__ import annotations

import asyncio
import logging
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

import src.core.pipeline as pipe_mod
from src.core.pipeline import EventPipeline, RunStateMissing


class FakeStore:
    def __init__(self) -> None:
        self.ingested: list[object] = []

    async def ingest(self, event: object) -> None:
        self.ingested.append(event)


class FakeRAG:
    async def embed(self, *_a: object, **_kw: object) -> list[float]:
        return []

    async def upsert(self, *_a: object, **_kw: object) -> None:
        return None


class FakeSchema:
    async def ensure_life_areas(self, *_a: object, **_kw: object) -> None:
        return None

    async def upsert_node(self, *_a: object, **_kw: object) -> None:
        return None


class FakeGov:
    async def check(self, *_a: object, **_kw: object) -> SimpleNamespace:
        return SimpleNamespace(allowed=True, requires_approval=False, reason="ok")


class FakeAgents:
    pass


def _make_pipeline(monkeypatch: pytest.MonkeyPatch) -> EventPipeline:
    async def fake_record_history(**_kw: object) -> str:
        return "hist"

    monkeypatch.setattr("src.core.history.record_history", fake_record_history)
    return EventPipeline(FakeStore(), FakeRAG(), FakeSchema(), FakeGov(), FakeAgents())


@pytest.fixture
def mock_pipeline_metrics_inc(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    m = MagicMock()
    monkeypatch.setattr(pipe_mod._pipeline_metrics, "inc", m)
    return m


def test_pipeline_no_run_id_warning_and_metric(
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
    mock_pipeline_metrics_inc: MagicMock,
) -> None:
    monkeypatch.delenv("PIPELINE_RUN_POLICY", raising=False)
    caplog.set_level(logging.WARNING)

    async def _go() -> None:
        pipe = _make_pipeline(monkeypatch)
        await pipe.run(
            tenant_id="t1",
            space_id="s1",
            user_id="u1",
            source="notion",
            content="hello",
            metadata={},
            event_type="ingest",
        )

    asyncio.run(_go())
    assert "PIPELINE_NO_RUN_ID" in caplog.text
    assert "tenant_id=t1" in caplog.text
    mock_pipeline_metrics_inc.assert_any_call(
        "no_run_id_total",
        labels={"event_type": "ingest", "source": "notion"},
    )


def test_pipeline_orphan_run_id_error_and_metric(
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
    mock_pipeline_metrics_inc: MagicMock,
) -> None:
    monkeypatch.delenv("PIPELINE_RUN_POLICY", raising=False)
    caplog.set_level(logging.ERROR)
    monkeypatch.delenv("STRICT_RUN_BOUNDARY_FAIL_FAST", raising=False)

    async def _go() -> None:
        pipe = _make_pipeline(monkeypatch)
        await pipe.run(
            tenant_id="t1",
            space_id="s1",
            user_id="u1",
            source="connector",
            content="hello",
            metadata={"run_id": "run_no_controller_state_xyz"},
            event_type="ingest",
        )

    asyncio.run(_go())
    assert "PIPELINE_ORPHAN_RUN_ID" in caplog.text
    assert "run_no_controller_state_xyz" in caplog.text
    mock_pipeline_metrics_inc.assert_any_call(
        "orphan_run_id_total",
        labels={"event_type": "ingest", "source": "connector"},
    )


def test_pipeline_orphan_run_id_strict_raises_run_state_missing(
    monkeypatch: pytest.MonkeyPatch,
    mock_pipeline_metrics_inc: MagicMock,
) -> None:
    monkeypatch.delenv("PIPELINE_RUN_POLICY", raising=False)
    monkeypatch.setenv("STRICT_RUN_BOUNDARY_FAIL_FAST", "1")

    async def _go() -> None:
        pipe = _make_pipeline(monkeypatch)
        await pipe.run(
            tenant_id="t1",
            space_id="s1",
            user_id="u1",
            source="connector",
            content="hello",
            metadata={"run_id": "run_strict_orphan"},
            event_type="ingest",
        )

    with pytest.raises(RunStateMissing, match="run_missing_state"):
        asyncio.run(_go())
    mock_pipeline_metrics_inc.assert_any_call(
        "orphan_run_id_total",
        labels={"event_type": "ingest", "source": "connector"},
    )


def test_run_state_missing_is_value_error_subclass() -> None:
    assert issubclass(RunStateMissing, ValueError)


def test_pipeline_run_policy_strict_missing_run_id_raises(
    monkeypatch: pytest.MonkeyPatch,
    mock_pipeline_metrics_inc: MagicMock,
) -> None:
    monkeypatch.setenv("PIPELINE_RUN_POLICY", "strict")
    monkeypatch.delenv("STRICT_RUN_BOUNDARY_FAIL_FAST", raising=False)

    async def _go() -> None:
        pipe = _make_pipeline(monkeypatch)
        await pipe.run(
            tenant_id="t1",
            space_id="s1",
            user_id="u1",
            source="notion",
            content="hello",
            metadata={},
            event_type="ingest",
        )

    with pytest.raises(RunStateMissing, match="PIPELINE_RUN_ID_REQUIRED"):
        asyncio.run(_go())
    mock_pipeline_metrics_inc.assert_any_call(
        "no_run_id_total",
        labels={"event_type": "ingest", "source": "notion"},
    )


def test_pipeline_run_policy_strict_orphan_raises(
    monkeypatch: pytest.MonkeyPatch,
    mock_pipeline_metrics_inc: MagicMock,
) -> None:
    monkeypatch.setenv("PIPELINE_RUN_POLICY", "strict")
    monkeypatch.delenv("STRICT_RUN_BOUNDARY_FAIL_FAST", raising=False)

    async def _go() -> None:
        pipe = _make_pipeline(monkeypatch)
        await pipe.run(
            tenant_id="t1",
            space_id="s1",
            user_id="u1",
            source="connector",
            content="hello",
            metadata={"run_id": "run_orphan_policy_strict"},
            event_type="ingest",
        )

    with pytest.raises(RunStateMissing, match="PIPELINE_RUN_STATE_MISSING"):
        asyncio.run(_go())
    mock_pipeline_metrics_inc.assert_any_call(
        "orphan_run_id_total",
        labels={"event_type": "ingest", "source": "connector"},
    )
