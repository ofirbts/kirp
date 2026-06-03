from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from scripts.orp_latency import _percentile, evaluate_latency_threshold
from scripts import orp_program as orp


def test_operational_readiness_program_json_structure() -> None:
    data = json.loads(
        (Path(__file__).resolve().parents[1] / "scripts" / "operational_readiness_program.json").read_text(
            encoding="utf-8"
        )
    )
    assert data["duration_days"] == 7
    assert len(data["days"]) == 7
    assert "go_no_go" in data
    for day in data["days"]:
        assert day["checklist"]
        assert day["evidence_required"]
        assert day["acceptance_criteria"]


def test_program_day_number_bounds() -> None:
    start = date(2026, 6, 1)
    assert orp.program_day_number(start, date(2026, 6, 1)) == 1
    assert orp.program_day_number(start, date(2026, 6, 7)) == 7
    assert orp.program_day_number(start, date(2026, 6, 15)) == 7


def test_percentile_empty() -> None:
    assert _percentile([], 95) == 0.0


def test_evaluate_latency_threshold_local_pass() -> None:
    report = {"summary": {"p95_sec": 90.0}}
    out = evaluate_latency_threshold(
        report, is_staging=False, max_local_p95=180, max_staging_p95=120
    )
    assert out["passed"] is True


def test_evaluate_latency_threshold_staging_fail() -> None:
    report = {"summary": {"p95_sec": 150.0}}
    out = evaluate_latency_threshold(
        report, is_staging=True, max_local_p95=180, max_staging_p95=120
    )
    assert out["passed"] is False


def test_go_no_go_no_evidence_is_no_go(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(orp, "ARTIFACTS", tmp_path)
    result = orp.evaluate_go_no_go(write_verdict_file=False)
    assert result["verdict"] == "NO-GO"
    assert result["blockers"]


def test_go_no_go_all_days_pass(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(orp, "ARTIFACTS", tmp_path)
    for d in range(1, 8):
        day_dir = tmp_path / f"day-{d:02d}"
        day_dir.mkdir(parents=True)
        payload = {
            "day": d,
            "overall": "pass",
            "consumer_hint": None,
            "checks": [],
        }
        if d == 5:
            payload["checks"] = [{"id": "latency_benchmark", "passed": True}]
        if d == 1:
            payload["checks"] = [
                {
                    "id": "health_snapshot",
                    "data": {"telemetry": {"governed_runtime_mode": "shadow"}},
                }
            ]
        (day_dir / "latest.json").write_text(json.dumps(payload), encoding="utf-8")
    result = orp.evaluate_go_no_go(write_verdict_file=False)
    assert result["verdict"] == "GO"
    assert not result["blockers"]


def test_orp_shell_wrappers_exist() -> None:
    root = Path(__file__).resolve().parents[1]
    for name in ("orp_init.sh", "orp_daily.sh", "orp_go_no_go.sh", "orp_status.sh"):
        path = root / "scripts" / name
        assert path.is_file()
        text = path.read_text(encoding="utf-8")
        assert "orp_program.py" in text


def test_run_day_writes_evidence(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(orp, "ARTIFACTS", tmp_path)
    monkeypatch.setattr(orp, "consumer_hint", lambda: None)
    monkeypatch.setattr(
        orp,
        "run_cmd",
        lambda *a, **k: {"passed": True, "exit_code": 0, "stdout": "ok", "stderr": ""},
    )
    monkeypatch.setattr(
        orp,
        "fetch_health",
        lambda _api: {
            "status": "healthy",
            "telemetry": {"ok": True, "governed_runtime_mode": "shadow"},
        },
    )
    monkeypatch.setattr(
        orp,
        "latency_run",
        lambda _api, _n: {
            "summary": {"samples_success": 3},
            "threshold": {"passed": True},
        },
    )
    rc = orp.run_day(1, api="http://127.0.0.1:8000")
    assert rc == 0
    latest = tmp_path / "day-01" / "latest.json"
    assert latest.is_file()
    data = json.loads(latest.read_text(encoding="utf-8"))
    assert data["overall"] == "pass"
    assert data["day"] == 1


def test_measure_ingest_latency_mocked(monkeypatch: pytest.MonkeyPatch) -> None:
    from scripts.orp_latency import measure_ingest_latency

    class FakeResp:
        status = 200

        def __enter__(self) -> "FakeResp":
            return self

        def __exit__(self, *args: object) -> None:
            return None

    monkeypatch.setattr("urllib.request.urlopen", lambda *a, **k: FakeResp())
    monkeypatch.setattr(
        "scripts.staging_tenant_helpers.poll_events_for_marker",
        lambda *a, **k: True,
    )
    out = measure_ingest_latency("http://127.0.0.1:8000", "token", samples=1, poll_timeout_sec=5)
    assert out["summary"]["samples_success"] == 1
