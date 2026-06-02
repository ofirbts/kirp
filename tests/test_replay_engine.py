from __future__ import annotations

import json

from src.telemetry.execution_graph import build_execution_graph
from src.telemetry.replay_engine import replay_from_graph, replay_timeline
from src.telemetry.trace_reconstructor import TraceStage, TraceTimeline, reconstruct_timeline


def _line(trace_id: str, stage: str, ts: str, **meta: object) -> str:
    payload = {
        "event": "telemetry_trace",
        "trace_id": trace_id,
        "stage": stage,
        "timestamp": ts,
    }
    payload.update(meta)
    return json.dumps(payload)


def _timeline(trace_id: str, lines: list[str]) -> TraceTimeline:
    return reconstruct_timeline(trace_id, lines)


def test_replay_deterministic_same_input() -> None:
    lines = [
        _line("tr-d", "kafka_received", "2026-06-02T10:00:01+00:00", event_id="e1"),
        _line("tr-d", "governance_before", "2026-06-02T10:00:02+00:00", event_id="e1"),
        _line("tr-d", "governance_after", "2026-06-02T10:00:03+00:00", event_id="e1", allowed=True),
    ]
    tl = _timeline("tr-d", lines)
    r1 = replay_timeline(tl)
    r2 = replay_timeline(tl)
    assert r1.deterministic_hash == r2.deterministic_hash
    assert r1.mode == "dry_run"
    assert len(r1.steps) == 3


def test_replay_partial_trace_no_crash() -> None:
    tl = TraceTimeline(
        trace_id="tr-partial",
        tenant_id="t1",
        started_at=None,
        completed_at=None,
        stages=(
            TraceStage(
                stage="kafka_received",
                timestamp=__import__("datetime").datetime(2026, 6, 2, 10, 0, 1, tzinfo=__import__("datetime").timezone.utc),
                metadata={"event_id": "e2"},
            ),
        ),
    )
    report = replay_timeline(tl)
    assert report.partial is True
    assert len(report.steps) == 1
    assert report.steps[0].outcome == "no_side_effects"


def test_replay_duplicate_stages() -> None:
    lines = [
        _line("tr-dup", "mongo_before", "2026-06-02T10:00:01+00:00", event_id="e3"),
        _line("tr-dup", "mongo_before", "2026-06-02T10:00:02+00:00", event_id="e3"),
    ]
    tl = _timeline("tr-dup", lines)
    report = replay_timeline(tl)
    assert len(report.steps) == 2
    assert report.steps[0].stage == report.steps[1].stage


def test_replay_governance_would_deny_observed() -> None:
    lines = [
        _line("tr-gov", "governance_before", "2026-06-02T10:00:01+00:00"),
        _line("tr-gov", "governance_after", "2026-06-02T10:00:02+00:00", allowed=False),
    ]
    tl = _timeline("tr-gov", lines)
    report = replay_timeline(tl)
    assert report.governance_would_block is True
    assert any(s.outcome == "would_deny" for s in report.steps)


def test_replay_from_graph_empty_edges_partial() -> None:
    tl = _timeline(
        "tr-graph",
        [_line("tr-graph", "agent_detection", "2026-06-02T10:00:01+00:00", potential_agents=["planner"])],
    )
    graph = build_execution_graph(tl)
    report = replay_from_graph(graph, tl)
    assert report.partial is True
    assert report.agents_observed == ("planner",)
    assert all(s.outcome == "agents_not_executed" for s in report.steps if s.stage == "agent_detection")


def test_replay_empty_timeline() -> None:
    tl = TraceTimeline("tr-empty", None, None, None, ())
    report = replay_timeline(tl)
    assert report.steps == ()
    assert report.partial is True
    assert report.deterministic_hash
