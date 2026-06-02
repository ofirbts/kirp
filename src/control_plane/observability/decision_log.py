from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class DecisionRecord:
    decision: str
    resource: str
    tenant_id: str | None
    details: dict[str, Any] = field(default_factory=dict)
    ts: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


def append_decision(
    sink: list[DecisionRecord],
    *,
    decision: str,
    resource: str,
    tenant_id: str | None = None,
    **details: Any,
) -> DecisionRecord:
    rec = DecisionRecord(decision=decision, resource=resource, tenant_id=tenant_id, details=dict(details))
    sink.append(rec)
    return rec
