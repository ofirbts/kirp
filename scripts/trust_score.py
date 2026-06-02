#!/usr/bin/env python3
"""Compute a deterministic system trust score from hardening artifacts."""

from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path


def read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except json.JSONDecodeError:
        return {}


def is_enforceable_incident(row: dict) -> bool:
    source = str(row.get("source", "")).strip().lower()
    if source in {"test", "manual"}:
        return False
    meta = row.get("meta")
    if isinstance(meta, dict) and bool(meta.get("synthetic")):
        return False
    return True


def parse_ts(ts: str) -> float:
    try:
        return time.mktime(time.strptime(ts, "%Y-%m-%dT%H:%M:%SZ"))
    except Exception:
        return 0.0


def recovery_cutoffs(rows: list[dict]) -> dict[str, float]:
    out: dict[str, float] = {}
    for row in rows:
        if str(row.get("type", "")).strip().lower() != "recovery":
            continue
        meta = row.get("meta")
        if not isinstance(meta, dict):
            continue
        target = str(meta.get("target_type", "")).strip().lower()
        if not target:
            continue
        ts = parse_ts(str(row.get("ts", "")))
        if ts > out.get(target, 0.0):
            out[target] = ts
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--perf-results", default="artifacts/perf/latest-results.json")
    parser.add_argument("--ux-results", default="artifacts/perf/user-perceived-results.json")
    parser.add_argument("--incident-log", default="artifacts/incidents/failures.jsonl")
    parser.add_argument("--drift-check-exit", type=int, default=0)
    parser.add_argument("--out", default="artifacts/perf/trust-score.json")
    parser.add_argument("--min-score", type=int, default=80)
    args = parser.parse_args()

    score = 100
    reasons: list[str] = []
    unknowns: list[str] = []

    perf = read_json(Path(args.perf_results))
    perf_flows = perf.get("flows", {}) if isinstance(perf.get("flows"), dict) else {}
    if not perf_flows:
        unknowns.append("perf_results_missing")
        score -= 25
    else:
        for flow_name, flow_data in perf_flows.items():
            if isinstance(flow_data, dict) and flow_data.get("status") == "fail":
                score -= 12
                reasons.append(f"perf_fail:{flow_name}")

    ux = read_json(Path(args.ux_results))
    ux_checks = ux.get("checks", {}) if isinstance(ux.get("checks"), dict) else {}
    if not ux_checks:
        unknowns.append("ux_results_missing")
        score -= 25
    else:
        for check_name, check_data in ux_checks.items():
            if isinstance(check_data, dict) and check_data.get("status") == "fail":
                score -= 12
                reasons.append(f"ux_fail:{check_name}")

    incident_path = Path(args.incident_log)
    if not incident_path.exists():
        unknowns.append("incident_log_missing")
        score -= 15
    else:
        incident_lines = [line for line in incident_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        enforceable_rows: list[dict] = []
        all_rows: list[dict] = []
        for line in incident_lines:
            try:
                row = json.loads(line)
                if isinstance(row, dict):
                    all_rows.append(row)
            except json.JSONDecodeError:
                continue
        cutoffs = recovery_cutoffs(all_rows)
        for row in all_rows:
            if not is_enforceable_incident(row):
                continue
            incident_type = str(row.get("type", "")).strip().lower()
            if not incident_type:
                continue
            ts = parse_ts(str(row.get("ts", "")))
            if ts <= cutoffs.get(incident_type, 0.0):
                continue
            enforceable_rows.append(row)
        auth_failures = 0
        fallback_usage = 0
        timeouts = 0
        for row in enforceable_rows:
            incident_type = str(row.get("type", "")).strip()
            if incident_type == "auth_failure":
                auth_failures += 1
            elif incident_type == "fallback_usage":
                fallback_usage += 1
            elif incident_type == "timeout":
                timeouts += 1
        score -= min(10, auth_failures * 2)
        score -= min(8, fallback_usage * 2)
        score -= min(8, timeouts * 2)
        if enforceable_rows:
            reasons.append(f"incident_count:{len(enforceable_rows)}")

    if args.drift_check_exit != 0:
        score -= 15
        reasons.append("contract_drift_failed")

    git_sha = (os.getenv("GITHUB_SHA", "") or "").strip()
    if not git_sha or git_sha == "unknown":
        unknowns.append("runtime_version_unknown")
        score -= 15

    score = max(0, min(100, score))
    remediation: list[str] = []
    if "perf_results_missing" in unknowns:
        remediation.append("Run scripts/perf_check.py to generate perf artifact.")
    if "ux_results_missing" in unknowns:
        remediation.append("Run scripts/ux_reality_check.py after Playwright setup.")
    if "runtime_version_unknown" in unknowns:
        remediation.append("Provide GITHUB_SHA/APP_GIT_SHA and verify runtime version headers.")
    if score < args.min_score:
        remediation.append("Resolve listed reasons and rerun trust score gate.")

    payload = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "score": score,
        "status": "pass" if score >= args.min_score and not unknowns else "degraded",
        "min_required": args.min_score,
        "reasons": reasons,
        "unknowns": unknowns,
        "remediation": remediation,
    }

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
    print(f"trust_score: {score}")
    if reasons:
        print("reasons:", ", ".join(reasons))
    if unknowns:
        print("unknowns:", ", ".join(unknowns))
    if score < args.min_score:
        print(f"trust_score: FAIL (< {args.min_score})")
        for step in remediation:
            print("remediation:", step)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
