from __future__ import annotations

from pathlib import Path

from src.telemetry.orchestration_trace import log_trace
from src.telemetry.trace_sink import append_telemetry_line, list_trace_ids_from_file
import logging


def test_append_telemetry_line_writes_file(tmp_path: Path, monkeypatch) -> None:
    log_file = tmp_path / "traces.jsonl"
    monkeypatch.setenv("KIRP_TRACE_LOG_PATH", str(log_file))
    ok = append_telemetry_line(
        {
            "event": "telemetry_trace",
            "trace_id": "tr-sink-1",
            "stage": "kafka_received",
            "timestamp": "2026-06-02T10:00:01+00:00",
            "tenant_id": "t1",
        }
    )
    assert ok is True
    text = log_file.read_text(encoding="utf-8")
    assert "tr-sink-1" in text


def test_log_trace_appends_to_sink(tmp_path: Path, monkeypatch) -> None:
    log_file = tmp_path / "live.jsonl"
    monkeypatch.setenv("KIRP_TRACE_LOG_PATH", str(log_file))
    log_trace(
        logging.getLogger("test_trace_sink"),
        "governance_after",
        trace_id="tr-sink-2",
        tenant_id="t1",
        allowed=True,
    )
    ids = list_trace_ids_from_file(str(log_file))
    assert ids == ("tr-sink-2",)


def test_list_trace_ids_orders_by_count(tmp_path: Path) -> None:
    log_file = tmp_path / "list.jsonl"
    log_file.write_text(
        "\n".join(
            [
                '{"event":"telemetry_trace","trace_id":"a","stage":"s1","timestamp":"2026-06-02T10:00:01+00:00"}',
                '{"event":"telemetry_trace","trace_id":"b","stage":"s1","timestamp":"2026-06-02T10:00:01+00:00"}',
                '{"event":"telemetry_trace","trace_id":"a","stage":"s2","timestamp":"2026-06-02T10:00:02+00:00"}',
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    ids = list_trace_ids_from_file(str(log_file), limit=10)
    assert ids[0] == "a"
    assert "b" in ids
