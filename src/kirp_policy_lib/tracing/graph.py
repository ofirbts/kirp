from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class TraceNode:
    node_id: str
    step: str
    fields: tuple[tuple[str, Any], ...]
    children: tuple[TraceNode, ...] = ()


@dataclass(frozen=True)
class DecisionTrace:
    trace_id: str
    root: TraceNode
    verdict: str
    reason: str


class DecisionTraceBuilder:
    def __init__(self, trace_id: str) -> None:
        self._trace_id = trace_id
        self._counter = 0
        self._steps: list[TraceNode] = []

    def _nid(self) -> str:
        self._counter += 1
        return f"n{self._counter}"

    def emit(self, step: str, **fields: Any) -> None:
        self._steps.append(TraceNode(self._nid(), step, tuple(fields.items()), ()))

    def build(self, verdict: str, reason: str) -> DecisionTrace:
        root = TraceNode(
            "root",
            "evaluation",
            (("trace_id", self._trace_id),),
            tuple(self._steps),
        )
        return DecisionTrace(self._trace_id, root, verdict, reason)


def flatten_trace_to_rows(trace: DecisionTrace) -> tuple[dict[str, object], ...]:
    rows: list[dict[str, object]] = []

    def walk(n: TraceNode) -> None:
        base: dict[str, object] = {"node_id": n.node_id, "step": n.step}
        base.update(dict(n.fields))
        rows.append(base)
        for c in n.children:
            walk(c)

    walk(trace.root)
    return tuple(rows)
