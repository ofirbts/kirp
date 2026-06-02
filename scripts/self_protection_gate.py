#!/usr/bin/env python3
"""Block unsafe deploy conditions from generated artifacts and checks."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time


def read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except json.JSONDecodeError:
        return {}


def run(cmd: list[str]) -> tuple[int, str]:
    p = subprocess.run(cmd, capture_output=True, text=True)
    return p.returncode, (p.stdout + p.stderr).strip()


def parse_enforced_rules(rules_file: Path) -> list[dict]:
    if not rules_file.exists():
        return []
    text = rules_file.read_text(encoding="utf-8")
    m = re.search(
        r"## Enforced Constraints \(machine-readable\)\s*```json\s*([\s\S]*?)\s*```",
        text,
    )
    if not m:
        return []
    try:
        data = json.loads(m.group(1))
    except json.JSONDecodeError:
        return []
    rules = data.get("rules", [])
    return rules if isinstance(rules, list) else []


def parse_iso(ts: str) -> float:
    try:
        return time.mktime(time.strptime(ts, "%Y-%m-%dT%H:%M:%SZ"))
    except Exception:
        return 0.0


def is_enforceable_incident(row: dict) -> bool:
    source = str(row.get("source", "")).strip().lower()
    if source in {"test", "manual"}:
        return False
    meta = row.get("meta")
    if isinstance(meta, dict) and bool(meta.get("synthetic")):
        return False
    return True


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
        ts = parse_iso(str(row.get("ts", "")))
        if ts > out.get(target, 0.0):
            out[target] = ts
    return out


def remediation_for(item: str) -> str:
    mapping = {
        "unknown_runtime_version": "Set GITHUB_SHA/APP_GIT_SHA and verify /health version fields.",
        "unknown_perf_metrics": "Run scripts/perf_check.py to generate artifacts/perf/latest-results.json.",
        "unknown_ux_latency": "Run scripts/ux_reality_check.py after Playwright setup.",
        "unknown_failure_pattern": "Run scripts/incident_memory.py analyze to initialize incident log.",
    }
    for key, value in mapping.items():
        if item.startswith(key):
            return value
    if item.startswith("auto_rule_enforced:"):
        return "Use KIRP_RULE_OVERRIDE_IDS for temporary override, then review incidents and fix root cause."
    if item.startswith("trend_up:"):
        return "Investigate increasing trend and reduce incident frequency before deploy."
    if item.startswith("auth_failure_spike:"):
        return "Investigate auth 401/403 causes and verify token refresh consistency."
    return "Inspect gate logs and fix underlying contract/performance issue."


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--perf-results", default="artifacts/perf/latest-results.json")
    parser.add_argument("--ux-results", default="artifacts/perf/user-perceived-results.json")
    parser.add_argument("--incident-log", default="artifacts/incidents/failures.jsonl")
    parser.add_argument("--rules-file", default=".cursor/rules/auto-learned.mdc")
    parser.add_argument("--auth-failure-threshold", type=int, default=5)
    parser.add_argument("--mode", choices=["local", "deploy"], default="deploy")
    args = parser.parse_args()

    failures: list[str] = []
    warnings: list[str] = []
    now = time.time()
    override_ids = {
        value.strip()
        for value in (os.getenv("KIRP_RULE_OVERRIDE_IDS", "") or "").split(",")
        if value.strip()
    }
    git_sha = (
        os.getenv("GITHUB_SHA", "")
        or os.getenv("APP_GIT_SHA", "")
        or ""
    ).strip()
    if not git_sha or git_sha == "unknown":
        code_git, out_git = run(["git", "rev-parse", "HEAD"])
        if code_git == 0 and out_git.strip():
            git_sha = out_git.strip()[:40]
    if not git_sha or git_sha == "unknown":
        if args.mode == "local":
            warnings.append("unknown_runtime_version")
        else:
            failures.append("unknown_runtime_version")

    code, output = run([sys.executable, "scripts/version_check.py"])
    if code != 0:
        failures.append(f"version_check_failed: {output}")

    code, output = run([sys.executable, "scripts/auth_consistency_check.py"])
    if code != 0:
        failures.append(f"auth_consistency_failed: {output}")

    perf = read_json(Path(args.perf_results))
    flows = perf.get("flows", {}) if isinstance(perf.get("flows"), dict) else {}
    if not flows:
        failures.append("unknown_perf_metrics")
    for flow_name, flow_data in flows.items():
        if isinstance(flow_data, dict) and flow_data.get("status") == "fail":
            failures.append(f"perf_degradation:{flow_name}")

    ux = read_json(Path(args.ux_results))
    checks = ux.get("checks", {}) if isinstance(ux.get("checks"), dict) else {}
    if not checks:
        failures.append("unknown_ux_latency")
    for check_name, check_data in checks.items():
        if isinstance(check_data, dict) and check_data.get("status") == "fail":
            failures.append(f"user_perceived_regression:{check_name}")

    incident_path = Path(args.incident_log)
    type_counts: dict[str, int] = {}
    all_rows: list[dict] = []
    if incident_path.exists():
        auth_failures = 0
        for line in incident_path.read_text(encoding="utf-8").splitlines():
            if '"type": "' in line:
                try:
                    parsed = json.loads(line)
                    if not isinstance(parsed, dict):
                        continue
                    all_rows.append(parsed)
                    if not is_enforceable_incident(parsed):
                        continue
                    incident_type = str(parsed.get("type", "")).strip()
                    if incident_type:
                        type_counts[incident_type] = type_counts.get(incident_type, 0) + 1
                except json.JSONDecodeError:
                    continue
        cutoffs = recovery_cutoffs(all_rows)
        type_counts = {
            k: v
            for k, v in type_counts.items()
            if k
        }
        # Recompute counts after recovery cutoffs.
        type_counts = {}
        for row in all_rows:
            if not is_enforceable_incident(row):
                continue
            incident_type = str(row.get("type", "")).strip().lower()
            if not incident_type:
                continue
            ts = parse_iso(str(row.get("ts", "")))
            if ts <= cutoffs.get(incident_type, 0.0):
                continue
            type_counts[incident_type] = type_counts.get(incident_type, 0) + 1
        auth_failures = type_counts.get("auth_failure", 0)
        if auth_failures >= args.auth_failure_threshold:
            failures.append(f"auth_failure_spike:{auth_failures}")
    else:
        failures.append("unknown_failure_pattern")

    auto_rules = parse_enforced_rules(Path(args.rules_file))
    for rule in auto_rules:
        rule_id = str(rule.get("id", "")).strip()
        if rule_id and rule_id in override_ids:
            warnings.append(f"rule_overridden:{rule_id}")
            continue
        expires_at = parse_iso(str(rule.get("expires_at", "")))
        if expires_at and expires_at < now:
            warnings.append(f"rule_expired:{rule_id}")
            continue
        incident_type = str(rule.get("incident_type", "")).strip()
        threshold = int(rule.get("threshold", 0) or 0)
        severity = str(rule.get("severity", "block")).strip().lower()
        if incident_type and threshold > 0:
            count = type_counts.get(incident_type, 0)
            if count >= threshold:
                entry = f"auto_rule_enforced:{rule.get('id', incident_type)}:{count}>={threshold}"
                if severity == "warn":
                    warnings.append(entry)
                else:
                    failures.append(entry)

    # Proactive trend pressure detection over incidents (last hour vs previous hour).
    if incident_path.exists():
        rows: list[dict] = []
        for line in incident_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                row = json.loads(line)
                if isinstance(row, dict):
                    if not is_enforceable_incident(row):
                        continue
                    rows.append(row)
            except json.JSONDecodeError:
                continue
        now = time.time()
        hour = 60 * 60
        for incident_type in ("timeout", "fallback_usage", "auth_failure"):
            recent = 0
            prev = 0
            for row in rows:
                if str(row.get("type", "")).strip() != incident_type:
                    continue
                ts = 0.0
                try:
                    ts = time.mktime(time.strptime(str(row.get("ts", "")), "%Y-%m-%dT%H:%M:%SZ"))
                except Exception:
                    ts = 0.0
                if ts >= now - hour:
                    recent += 1
                elif now - 2 * hour <= ts < now - hour:
                    prev += 1
            if recent > prev and recent >= 2:
                warnings.append(f"trend_up:{incident_type}:{prev}->{recent}")

    if failures:
        if args.mode == "local" and len(failures) >= 2:
            print("self_protection_gate: RESTRICTED")
            for item in failures:
                print(f"- {item}")
                print(f"  remediation: {remediation_for(item)}")
            for item in warnings:
                print(f"- warning:{item}")
                print(f"  remediation: {remediation_for(item)}")
            return 0
        print("self_protection_gate: FAIL")
        for item in failures:
            print(f"- {item}")
            print(f"  remediation: {remediation_for(item)}")
        for item in warnings:
            print(f"- warning:{item}")
            print(f"  remediation: {remediation_for(item)}")
        return 1

    print("self_protection_gate: ok")
    for item in warnings:
        print(f"- warning:{item}")
        print(f"  remediation: {remediation_for(item)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
