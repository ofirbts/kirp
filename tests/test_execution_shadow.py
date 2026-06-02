from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.telemetry.execution_shadow import (
    ShadowExecution,
    build_shadow_execution_response,
    emit_shadow_execution_observation,
    list_shadow_traces_from_file,
    simulate_execution_shadow,
)
from src.telemetry.trace_reconstructor import TraceStage, TraceTimeline, reconstruct_timeline


def _line(trace_id: str, stage: str, ts: str, **meta: object) -> str:
    payload = {
        "event": "telemetry_trace",
        "trace_id": trace_id,
        "stage": stage,
        "timestamp": ts,
        "tenant_id": "t1",
    }
    payload.update(meta)
    return json.dumps(payload)


def _timeline(trace_id: str, lines: list[str]) -> TraceTimeline:
    return reconstruct_timeline(trace_id, lines)


def test_shadow_simulation_deterministic() -> None:
    lines = [
        _line("tr-shadow", "governance_after", "2026-06-02T10:00:01+00:00", allowed=True, event_id="e1"),
    ]
    tl = _timeline("tr-shadow", lines)
    r1 = simulate_execution_shadow(tl, event_id="e1", hook_source="test")
    r2 = simulate_execution_shadow(tl, event_id="e1", hook_source="test")
    assert r1.deterministic_hash == r2.deterministic_hash


def test_shadow_governance_deny_blocks_execute() -> None:
    lines = [
        _line("tr-deny", "governance_after", "2026-06-02T10:00:01+00:00", allowed=False, event_id="e2"),
    ]
    tl = _timeline("tr-deny", lines)
    report = simulate_execution_shadow(tl, event_id="e2")
    assert report.would_governance_pass is False
    assert report.would_be_blocked is True
    assert report.would_execute is False
    assert all(not s.would_execute for s in report.shadow_executions if s.action_type != "governance_write")


def test_shadow_consistent_with_pipeline_governance_log() -> None:
    lines = [
        _line("tr-ok", "governance_after", "2026-06-02T10:00:01+00:00", allowed=True, requires_approval=False),
    ]
    tl = _timeline("tr-ok", lines)
    report = simulate_execution_shadow(
        tl,
        governance_allowed=True,
        governance_requires_approval=False,
    )
    assert report.would_governance_pass is True
    assert report.governance_outcome_prediction.startswith("would_allow")


def test_emit_shadow_does_not_call_execution_engine(tmp_path: Path) -> None:
    log_file = tmp_path / "traces.jsonl"
    with patch("src.telemetry.trace_sink.trace_log_path", return_value=str(log_file)):
        with patch("src.core.execution_engine.execute_command", new_callable=AsyncMock) as execute_mock:
            with patch("src.modules.m3.governance.send_m3_whatsapp_escalation", new_callable=AsyncMock) as wa_mock:
                report = emit_shadow_execution_observation(
                    trace_id="tr-emit",
                    event_id="e3",
                    tenant_id="t1",
                    hook_source="pipeline",
                    event_type="m3.reflection",
                    governance_allowed=True,
                    governance_requires_approval=True,
                )
    assert report is not None
    execute_mock.assert_not_called()
    wa_mock.assert_not_called()
    stored = list_shadow_traces_from_file("tr-emit", str(log_file))
    assert len(stored) == 1
    assert stored[0]["event"] == "shadow_execution_trace"


def test_build_shadow_response_from_timeline(tmp_path: Path) -> None:
    log_file = tmp_path / "live.jsonl"
    log_file.write_text(
        _line("demo-trace-1", "governance_after", "2026-06-02T10:00:03+00:00", allowed=True, event_id="e1")
        + "\n",
        encoding="utf-8",
    )
    with patch("src.telemetry.execution_shadow.trace_log_path", return_value=str(log_file)):
        body = build_shadow_execution_response("demo-trace-1", str(log_file))
    assert body["trace_id"] == "demo-trace-1"
    trace = body["shadow_execution_trace"]
    assert trace["would_governance_pass"] is True
    assert "shadow_executions" in trace


def test_shadow_api_route() -> None:
    from fastapi.testclient import TestClient
    from src.main import app
    import tempfile

    lines = [
        _line("api-tr", "governance_after", "2026-06-02T10:00:01+00:00", allowed=True),
    ]
    fd, name = tempfile.mkstemp(suffix=".jsonl")
    import os

    os.close(fd)
    Path(name).write_text("\n".join(lines) + "\n", encoding="utf-8")
    with patch("src.api.v1_trace.trace_log_path", return_value=name):
        client = TestClient(app)
        r = client.get("/api/v1/shadow-execution/api-tr")
    assert r.status_code == 200
    data = r.json()
    assert data["trace_id"] == "api-tr"
    assert data["shadow_execution_trace"]["would_governance_pass"] is True
