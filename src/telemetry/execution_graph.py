from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from src.telemetry.trace_reconstructor import TraceTimeline


@dataclass(frozen=True)
class ExecutionNode:
    stage: str
    timestamp: datetime
    metadata: dict[str, Any]


@dataclass(frozen=True)
class ExecutionEdge:
    source_stage: str
    target_stage: str
    relationship: str


@dataclass(frozen=True)
class ExecutionGraph:
    trace_id: str
    nodes: tuple[ExecutionNode, ...]
    edges: tuple[ExecutionEdge, ...]


@dataclass(frozen=True)
class ExecutionGraphSummary:
    total_nodes: int
    total_edges: int
    detected_failures: int
    missing_links: int
    governance_observed: bool
    agents_detected: tuple[str, ...]


def _first_index(stages: list[str], value: str) -> int | None:
    try:
        return stages.index(value)
    except ValueError:
        return None


def _add_edge(
    edges: list[ExecutionEdge],
    edge_keys: set[tuple[int, int, str]],
    src_idx: int,
    dst_idx: int,
    src_stage: str,
    dst_stage: str,
    relationship: str,
) -> None:
    if src_idx >= dst_idx:
        return
    key = (src_idx, dst_idx, relationship)
    if key in edge_keys:
        return
    edge_keys.add(key)
    edges.append(
        ExecutionEdge(
            source_stage=src_stage,
            target_stage=dst_stage,
            relationship=relationship,
        )
    )


def build_execution_graph(timeline: TraceTimeline) -> ExecutionGraph:
    nodes = tuple(
        ExecutionNode(stage=s.stage, timestamp=s.timestamp, metadata=s.metadata)
        for s in timeline.stages
    )
    edges: list[ExecutionEdge] = []
    edge_keys: set[tuple[int, int, str]] = set()
    stages = [n.stage for n in nodes]

    for i in range(len(nodes) - 1):
        _add_edge(
            edges,
            edge_keys,
            i,
            i + 1,
            nodes[i].stage,
            nodes[i + 1].stage,
            "chronological_next",
        )

    event_last_seen: dict[str, int] = {}
    for idx, node in enumerate(nodes):
        ev = node.metadata.get("event_id")
        if not isinstance(ev, str) or not ev:
            continue
        prev = event_last_seen.get(ev)
        if prev is not None:
            _add_edge(
                edges,
                edge_keys,
                prev,
                idx,
                nodes[prev].stage,
                node.stage,
                "same_event_id",
            )
        event_last_seen[ev] = idx

    g_before = _first_index(stages, "governance_before")
    g_after = _first_index(stages, "governance_after")
    if g_before is not None and g_after is not None:
        _add_edge(
            edges,
            edge_keys,
            g_before,
            g_after,
            nodes[g_before].stage,
            nodes[g_after].stage,
            "governance_transition",
        )

    kafka_idx = _first_index(stages, "kafka_received")
    if kafka_idx is not None:
        for idx, stage in enumerate(stages):
            if stage in {"governance_before", "governance_after", "rag_before", "mongo_before"}:
                _add_edge(
                    edges,
                    edge_keys,
                    kafka_idx,
                    idx,
                    nodes[kafka_idx].stage,
                    nodes[idx].stage,
                    "kafka_to_pipeline",
                )

    for idx, stage in enumerate(stages):
        if stage != "agent_detection":
            continue
        for dst in range(idx + 1, len(nodes)):
            _add_edge(
                edges,
                edge_keys,
                idx,
                dst,
                nodes[idx].stage,
                nodes[dst].stage,
                "agent_detection_downstream",
            )
            break

    return ExecutionGraph(trace_id=timeline.trace_id, nodes=nodes, edges=tuple(edges))


def summarize_execution_graph(graph: ExecutionGraph) -> ExecutionGraphSummary:
    detected_failures = 0
    governance_observed = False
    agents: list[str] = []
    stages = [n.stage for n in graph.nodes]

    for node in graph.nodes:
        if "failed" in node.stage:
            detected_failures += 1
        status = node.metadata.get("status")
        if isinstance(status, str) and status.lower() in {"error", "failed"}:
            detected_failures += 1
        allowed = node.metadata.get("allowed")
        if allowed is False:
            detected_failures += 1
        if node.stage in {"governance_before", "governance_after"}:
            governance_observed = True
        potential_agents = node.metadata.get("potential_agents")
        if isinstance(potential_agents, list):
            for a in potential_agents:
                if isinstance(a, str) and a and a not in agents:
                    agents.append(a)

    missing_links = 0
    if "governance_before" in stages and "governance_after" not in stages:
        missing_links += 1
    if "kafka_received" in stages and not any(
        s in stages for s in {"governance_before", "governance_after", "rag_before", "mongo_before"}
    ):
        missing_links += 1
    if "agent_detection" in stages and len(stages) == 1:
        missing_links += 1

    return ExecutionGraphSummary(
        total_nodes=len(graph.nodes),
        total_edges=len(graph.edges),
        detected_failures=detected_failures,
        missing_links=missing_links,
        governance_observed=governance_observed,
        agents_detected=tuple(agents),
    )

