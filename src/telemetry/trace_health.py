from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from src.telemetry.trace_sink import list_trace_ids_from_file, trace_log_path


@dataclass(frozen=True)
class TraceHealthReport:
    log_path: str | None
    log_exists: bool
    log_readable: bool
    total_trace_ids: int
    sample_trace_ids: tuple[str, ...]
    governed_runtime_mode: str
    baseline_fingerprint_configured: bool
    decision_log_path: str | None
    ok: bool
    issues: tuple[str, ...]


def probe_trace_health(*, limit: int = 100) -> TraceHealthReport:
    log_path = trace_log_path() or None
    issues: list[str] = []
    log_exists = False
    log_readable = False
    total = 0
    sample_trace_ids: tuple[str, ...] = ()
    if not log_path:
        issues.append("KIRP_TRACE_LOG_PATH not set")
    else:
        log_exists = os.path.exists(log_path)
        if not log_exists:
            issues.append("trace log file missing")
        else:
            try:
                trace_ids = list_trace_ids_from_file(log_path, limit=limit)
                log_readable = True
                total = len(trace_ids)
                sample_trace_ids = trace_ids
                if total == 0:
                    issues.append("trace log has no telemetry_trace rows")
            except Exception:
                issues.append("trace log file not readable")
    mode = (os.getenv("KIRP_GOVERNED_RUNTIME_MODE") or "shadow").strip().lower()
    baseline_fp = (os.getenv("KIRP_POLICY_BASELINE_FINGERPRINT") or "").strip()
    decision_path = (os.getenv("KIRP_DECISION_LOG_PATH") or "").strip() or None
    if mode == "enforce" and not baseline_fp:
        issues.append("enforce mode without KIRP_POLICY_BASELINE_FINGERPRINT")
    ok = len(issues) == 0
    return TraceHealthReport(
        log_path=log_path,
        log_exists=log_exists,
        log_readable=log_readable,
        total_trace_ids=total,
        sample_trace_ids=sample_trace_ids,
        governed_runtime_mode=mode,
        baseline_fingerprint_configured=bool(baseline_fp),
        decision_log_path=decision_path,
        ok=ok,
        issues=tuple(issues),
    )


def trace_health_to_dict(report: TraceHealthReport) -> dict[str, Any]:
    return {
        "ok": report.ok,
        "log_path": report.log_path,
        "log_exists": report.log_exists,
        "log_readable": report.log_readable,
        "total_trace_ids": report.total_trace_ids,
        "sample_trace_ids": list(report.sample_trace_ids),
        "governed_runtime_mode": report.governed_runtime_mode,
        "baseline_fingerprint_configured": report.baseline_fingerprint_configured,
        "decision_log_path": report.decision_log_path,
        "issues": list(report.issues),
    }
