from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from src.telemetry.replay_engine import ReplayReport


@dataclass(frozen=True)
class DecisionMemoryEntry:
    key: str
    value: str
    confidence: float
    source_stage: str
    evidence: dict[str, Any]


@dataclass(frozen=True)
class DecisionMemorySnapshot:
    trace_id: str
    tenant_id: str | None
    entries: tuple[DecisionMemoryEntry, ...]
    fingerprint: str


def _bounded_confidence(value: float) -> float:
    if value < 0.0:
        return 0.0
    if value > 1.0:
        return 1.0
    return value


def build_decision_memory(report: ReplayReport) -> DecisionMemorySnapshot:
    entries: list[DecisionMemoryEntry] = []
    if report.governance_would_block:
        entries.append(
            DecisionMemoryEntry(
                key="governance.last_outcome",
                value="would_deny",
                confidence=0.95,
                source_stage="governance_after",
                evidence={"trace_id": report.trace_id},
            )
        )
    elif any(step.stage == "governance_after" for step in report.steps):
        entries.append(
            DecisionMemoryEntry(
                key="governance.last_outcome",
                value="would_allow",
                confidence=0.9,
                source_stage="governance_after",
                evidence={"trace_id": report.trace_id},
            )
        )

    if report.agents_observed:
        entries.append(
            DecisionMemoryEntry(
                key="agents.detected",
                value=",".join(report.agents_observed),
                confidence=0.85,
                source_stage="agent_detection",
                evidence={"count": len(report.agents_observed)},
            )
        )

    failures = [step.stage for step in report.steps if "failed" in step.stage or step.outcome == "failure_observed"]
    if failures:
        entries.append(
            DecisionMemoryEntry(
                key="pipeline.failure_stages",
                value=",".join(failures),
                confidence=0.9,
                source_stage=failures[0],
                evidence={"count": len(failures)},
            )
        )

    if report.partial:
        entries.append(
            DecisionMemoryEntry(
                key="trace.completeness",
                value="partial",
                confidence=0.8,
                source_stage=report.steps[-1].stage if report.steps else "unknown",
                evidence={"steps": len(report.steps)},
            )
        )

    ordered = sorted(entries, key=lambda e: (e.key, e.value, e.source_stage))
    canonical = json.dumps(
        [
            {
                "key": entry.key,
                "value": entry.value,
                "confidence": _bounded_confidence(entry.confidence),
                "source_stage": entry.source_stage,
                "evidence": entry.evidence,
            }
            for entry in ordered
        ],
        sort_keys=True,
    )
    fingerprint = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return DecisionMemorySnapshot(
        trace_id=report.trace_id,
        tenant_id=report.tenant_id,
        entries=tuple(ordered),
        fingerprint=fingerprint,
    )


def decision_memory_to_dict(snapshot: DecisionMemorySnapshot) -> dict[str, Any]:
    return {
        "trace_id": snapshot.trace_id,
        "tenant_id": snapshot.tenant_id,
        "fingerprint": snapshot.fingerprint,
        "total_entries": len(snapshot.entries),
        "entries": [
            {
                "key": entry.key,
                "value": entry.value,
                "confidence": _bounded_confidence(entry.confidence),
                "source_stage": entry.source_stage,
                "evidence": entry.evidence,
            }
            for entry in snapshot.entries
        ],
    }
