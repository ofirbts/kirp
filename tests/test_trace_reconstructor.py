from __future__ import annotations

from src.telemetry.trace_reconstructor import reconstruct_timeline


def _telemetry_line(trace_id: str, stage: str, timestamp: str, **meta: object) -> str:
    payload = {
        "event": "telemetry_trace",
        "trace_id": trace_id,
        "stage": stage,
        "timestamp": timestamp,
    }
    payload.update(meta)
    import json

    return json.dumps(payload)


def test_chronological_ordering() -> None:
    lines = [
        _telemetry_line("tr-1", "stage_b", "2026-06-02T10:00:02+00:00"),
        _telemetry_line("tr-1", "stage_a", "2026-06-02T10:00:01+00:00"),
    ]
    timeline = reconstruct_timeline("tr-1", lines)
    assert [s.stage for s in timeline.stages] == ["stage_a", "stage_b"]
    assert timeline.started_at is not None
    assert timeline.completed_at is not None


def test_malformed_log_handling() -> None:
    lines = [
        "not-json",
        '{"event":"telemetry_trace","trace_id":"tr-2"}',
        _telemetry_line("tr-2", "ok", "2026-06-02T10:00:01+00:00"),
    ]
    timeline = reconstruct_timeline("tr-2", lines)
    assert len(timeline.stages) == 1
    assert timeline.stages[0].stage == "ok"


def test_partial_trace_reconstruction() -> None:
    lines = [
        _telemetry_line("tr-3", "kafka_received", "2026-06-02T10:00:01+00:00"),
        _telemetry_line("other", "ignore", "2026-06-02T10:00:02+00:00"),
    ]
    timeline = reconstruct_timeline("tr-3", lines)
    assert timeline.trace_id == "tr-3"
    assert len(timeline.stages) == 1
    assert timeline.completed_at == timeline.started_at


def test_duplicate_stage_handling() -> None:
    lines = [
        _telemetry_line("tr-4", "stage_x", "2026-06-02T10:00:01+00:00", event_id="ev-1"),
        _telemetry_line("tr-4", "stage_x", "2026-06-02T10:00:02+00:00", event_id="ev-1"),
    ]
    timeline = reconstruct_timeline("tr-4", lines)
    assert len(timeline.stages) == 2
    assert timeline.stages[0].stage == "stage_x"
    assert timeline.stages[1].stage == "stage_x"


def test_identical_duplicate_lines_deduped() -> None:
    line = _telemetry_line("tr-5", "kafka_received", "2026-06-02T10:00:01+00:00", event_id="ev-1")
    timeline = reconstruct_timeline("tr-5", [line, line])
    assert len(timeline.stages) == 1


def test_empty_trace_handling() -> None:
    timeline = reconstruct_timeline("tr-empty", [])
    assert timeline.trace_id == "tr-empty"
    assert timeline.started_at is None
    assert timeline.completed_at is None
    assert timeline.stages == ()

