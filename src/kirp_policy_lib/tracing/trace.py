from __future__ import annotations

from src.kirp_policy_lib.tracing.graph import TraceNode


def trace_depth(node: TraceNode) -> int:
    if not node.children:
        return 1
    return 1 + max(trace_depth(c) for c in node.children)


def trace_ordered_steps(root: TraceNode) -> tuple[str, ...]:
    out: list[str] = []

    def walk(n: TraceNode) -> None:
        if n.node_id != "root":
            out.append(n.step)
        for c in n.children:
            walk(c)

    walk(root)
    return tuple(out)
