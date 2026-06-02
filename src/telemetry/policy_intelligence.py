from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from src.telemetry.decision_memory import DecisionMemorySnapshot


@dataclass(frozen=True)
class PolicyDriftSignal:
    kind: str
    key: str
    baseline_value: str | None
    current_value: str | None
    severity: str


@dataclass(frozen=True)
class PolicyDriftReport:
    trace_id: str
    tenant_id: str | None
    baseline_fingerprint: str | None
    current_fingerprint: str
    drift_detected: bool
    drift_score: float
    signals: tuple[PolicyDriftSignal, ...]
    report_fingerprint: str


def _entry_map(snapshot: DecisionMemorySnapshot) -> dict[str, str]:
    return {entry.key: entry.value for entry in snapshot.entries}


def _severity_for_key_change(key: str) -> str:
    if key == "governance.last_outcome":
        return "critical"
    if key in {"pipeline.failure_stages", "trace.completeness"}:
        return "high"
    return "medium"


def _score_from_signals(signals: list[PolicyDriftSignal]) -> float:
    weights = {"critical": 1.0, "high": 0.7, "medium": 0.4, "low": 0.2}
    if not signals:
        return 0.0
    total = sum(weights.get(s.severity, 0.3) for s in signals)
    return min(1.0, round(total / max(len(signals), 1), 4))


def _report_fingerprint(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def compare_decision_memory(
    current: DecisionMemorySnapshot,
    baseline: DecisionMemorySnapshot,
) -> PolicyDriftReport:
    signals: list[PolicyDriftSignal] = []
    if current.fingerprint != baseline.fingerprint:
        signals.append(
            PolicyDriftSignal(
                kind="fingerprint_mismatch",
                key="*",
                baseline_value=baseline.fingerprint,
                current_value=current.fingerprint,
                severity="high",
            )
        )
    base_map = _entry_map(baseline)
    cur_map = _entry_map(current)
    for key in sorted(set(base_map) | set(cur_map)):
        b_val = base_map.get(key)
        c_val = cur_map.get(key)
        if b_val is None and c_val is not None:
            signals.append(
                PolicyDriftSignal(
                    kind="entry_added",
                    key=key,
                    baseline_value=None,
                    current_value=c_val,
                    severity=_severity_for_key_change(key),
                )
            )
            continue
        if c_val is None and b_val is not None:
            signals.append(
                PolicyDriftSignal(
                    kind="entry_removed",
                    key=key,
                    baseline_value=b_val,
                    current_value=None,
                    severity=_severity_for_key_change(key),
                )
            )
            continue
        if b_val != c_val:
            signals.append(
                PolicyDriftSignal(
                    kind="entry_changed",
                    key=key,
                    baseline_value=b_val,
                    current_value=c_val,
                    severity=_severity_for_key_change(key),
                )
            )
    drift_score = _score_from_signals(signals)
    drift_detected = len(signals) > 0
    ordered_signals = tuple(sorted(signals, key=lambda s: (s.kind, s.key)))
    payload = {
        "trace_id": current.trace_id,
        "baseline_fingerprint": baseline.fingerprint,
        "current_fingerprint": current.fingerprint,
        "drift_detected": drift_detected,
        "drift_score": drift_score,
        "signals": [
            {
                "kind": s.kind,
                "key": s.key,
                "baseline_value": s.baseline_value,
                "current_value": s.current_value,
                "severity": s.severity,
            }
            for s in ordered_signals
        ],
    }
    return PolicyDriftReport(
        trace_id=current.trace_id,
        tenant_id=current.tenant_id,
        baseline_fingerprint=baseline.fingerprint,
        current_fingerprint=current.fingerprint,
        drift_detected=drift_detected,
        drift_score=drift_score,
        signals=ordered_signals,
        report_fingerprint=_report_fingerprint(payload),
    )


def compare_fingerprint_only(
    current: DecisionMemorySnapshot,
    baseline_fingerprint: str,
) -> PolicyDriftReport:
    baseline_fp = baseline_fingerprint.strip()
    match = current.fingerprint == baseline_fp
    signals: list[PolicyDriftSignal] = []
    if not match:
        signals.append(
            PolicyDriftSignal(
                kind="fingerprint_mismatch",
                key="*",
                baseline_value=baseline_fp,
                current_value=current.fingerprint,
                severity="high",
            )
        )
    drift_score = _score_from_signals(signals)
    ordered_signals = tuple(signals)
    payload = {
        "trace_id": current.trace_id,
        "baseline_fingerprint": baseline_fp,
        "current_fingerprint": current.fingerprint,
        "drift_detected": not match,
        "drift_score": drift_score,
        "signals": [
            {
                "kind": s.kind,
                "key": s.key,
                "baseline_value": s.baseline_value,
                "current_value": s.current_value,
                "severity": s.severity,
            }
            for s in ordered_signals
        ],
    }
    return PolicyDriftReport(
        trace_id=current.trace_id,
        tenant_id=current.tenant_id,
        baseline_fingerprint=baseline_fp or None,
        current_fingerprint=current.fingerprint,
        drift_detected=not match,
        drift_score=drift_score,
        signals=ordered_signals,
        report_fingerprint=_report_fingerprint(payload),
    )


def policy_drift_to_dict(report: PolicyDriftReport) -> dict[str, Any]:
    return {
        "trace_id": report.trace_id,
        "tenant_id": report.tenant_id,
        "baseline_fingerprint": report.baseline_fingerprint,
        "current_fingerprint": report.current_fingerprint,
        "drift_detected": report.drift_detected,
        "drift_score": report.drift_score,
        "report_fingerprint": report.report_fingerprint,
        "total_signals": len(report.signals),
        "signals": [
            {
                "kind": s.kind,
                "key": s.key,
                "baseline_value": s.baseline_value,
                "current_value": s.current_value,
                "severity": s.severity,
            }
            for s in report.signals
        ],
    }
