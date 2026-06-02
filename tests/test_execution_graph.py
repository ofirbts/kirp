from __future__ import annotations

from src.telemetry.execution_graph import build_execution_graph, summarize_execution_graph
from src.telemetry.trace_reconstructor import reconstruct_timeline


def _line(trace_id: str, stage: str, ts: str, **meta: object) -> str:
    import json

    payload = {
        "event": "telemetry_trace",
        "trace_id": trace_id,
        "stage": stage,
        "timestamp": ts,
    }
    payload.update(meta)
    return json.dumps(payload)


def test_graph_construction_with_governance_edge() -> None:
    tl = reconstruct_timeline(
        "tr-g1",
        [
            _line("tr-g1", "kafka_received", "2026-06-02T10:00:01+00:00", event_id="e1"),
            _line("tr-g1", "governance_before", "2026-06-02T10:00:02+00:00", event_id="e1"),
            _line("tr-g1", "governance_after", "2026-06-02T10:00:03+00:00", event_id="e1", allowed=True),
            _line("tr-g1", "mongo_before", "2026-06-02T10:00:04+00:00", event_id="e1"),
        ],
    )
    graph = build_execution_graph(tl)
    assert len(graph.nodes) == 4
    assert any(e.relationship == "governance_transition" for e in graph.edges)
    summary = summarize_execution_graph(graph)
    assert summary.governance_observed is True


def test_orphan_stages_are_kept() -> None:
    tl = reconstruct_timeline(
        "tr-orphan",
        [
            _line("tr-orphan", "agent_detection", "2026-06-02T10:00:01+00:00", potential_agents=["planner"]),
        ],
    )
    graph = build_execution_graph(tl)
    summary = summarize_execution_graph(graph)
    assert len(graph.nodes) == 1
    assert len(graph.edges) == 0
    assert summary.missing_links >= 1
    assert summary.agents_detected == ("planner",)


def test_duplicate_stages_supported() -> None:
    tl = reconstruct_timeline(
        "tr-dup",
        [
            _line("tr-dup", "mongo_before", "2026-06-02T10:00:01+00:00", event_id="e2"),
            _line("tr-dup", "mongo_before", "2026-06-02T10:00:02+00:00", event_id="e2"),
        ],
    )
    graph = build_execution_graph(tl)
    assert len(graph.nodes) == 2
    assert any(e.relationship == "same_event_id" for e in graph.edges)


def test_malformed_telemetry_tolerated() -> None:
    tl = reconstruct_timeline("tr-mal", ["not-json", '{"event":"other"}'])
    graph = build_execution_graph(tl)
    summary = summarize_execution_graph(graph)
    assert len(graph.nodes) == 0
    assert summary.total_edges == 0


def test_missing_governance_stage() -> None:
    tl = reconstruct_timeline(
        "tr-mg",
        [
            _line("tr-mg", "governance_before", "2026-06-02T10:00:01+00:00"),
            _line("tr-mg", "mongo_before", "2026-06-02T10:00:02+00:00"),
        ],
    )
    graph = build_execution_graph(tl)
    summary = summarize_execution_graph(graph)
    assert not any(e.relationship == "governance_transition" for e in graph.edges)
    assert summary.missing_links >= 1


def test_cyclic_protection_edges_go_forward_only() -> None:
    tl = reconstruct_timeline(
        "tr-cyc",
        [
            _line("tr-cyc", "a", "2026-06-02T10:00:01+00:00", event_id="e3"),
            _line("tr-cyc", "b", "2026-06-02T10:00:02+00:00", event_id="e3"),
            _line("tr-cyc", "a", "2026-06-02T10:00:03+00:00", event_id="e3"),
        ],
    )
    graph = build_execution_graph(tl)
    stage_positions: dict[str, list[int]] = {}
    for i, node in enumerate(graph.nodes):
        stage_positions.setdefault(node.stage, []).append(i)
    for edge in graph.edges:
        src = stage_positions[edge.source_stage][0]
        dst = stage_positions[edge.target_stage][-1]
        assert src <= dst

