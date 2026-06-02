from __future__ import annotations

from collections import deque
from typing import Iterator

from src.kirp_policy_lib.tracing.graph import DecisionTrace


class DecisionRecord:
    __slots__ = ("trace_id", "tenant_id", "decision", "trace")

    def __init__(
        self,
        trace_id: str,
        tenant_id: str | None,
        decision: str,
        trace: DecisionTrace,
    ) -> None:
        self.trace_id = trace_id
        self.tenant_id = tenant_id
        self.decision = decision
        self.trace = trace


class InMemoryDecisionLog:
    def __init__(self, max_entries: int = 10000) -> None:
        self._max = max(1, max_entries)
        self._q: deque[DecisionRecord] = deque(maxlen=self._max)

    def append_trace(self, trace: DecisionTrace, tenant_id: str | None, decision: str) -> None:
        self._q.append(DecisionRecord(trace.trace_id, tenant_id, decision, trace))

    def __len__(self) -> int:
        return len(self._q)

    def entries(self) -> tuple[DecisionRecord, ...]:
        return tuple(self._q)

    def iter_recent(self) -> Iterator[DecisionRecord]:
        return iter(self._q)

    def clear(self) -> None:
        self._q.clear()
