#!/usr/bin/env python3
"""Structured failure memory + auto-learned rule generation."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

DEFAULT_LOG = Path("artifacts/incidents/failures.jsonl")
DEFAULT_RULES = Path(".cursor/rules/auto-learned.mdc")
PATTERN_THRESHOLDS = {"timeout": 3, "auth_failure": 3, "fallback_usage": 5}
TREND_WINDOW_SECONDS = 60 * 60
RULE_REVIEW_HOURS = 24
RULE_EXPIRE_HOURS = 72


def append_incident(log_path: Path, payload: dict[str, Any]) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=True) + "\n")


def read_incidents(log_path: Path) -> list[dict[str, Any]]:
    if not log_path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in log_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
            if isinstance(row, dict):
                rows.append(row)
        except json.JSONDecodeError:
            continue
    return rows


def parse_ts(ts: str) -> float:
    try:
        return time.mktime(time.strptime(ts, "%Y-%m-%dT%H:%M:%SZ"))
    except Exception:
        return 0.0


def is_enforceable_incident(row: dict[str, Any]) -> bool:
    source = str(row.get("source", "")).strip().lower()
    if source in {"test", "manual"}:
        return False
    meta = row.get("meta")
    if isinstance(meta, dict) and bool(meta.get("synthetic")):
        return False
    return True


def recovery_cutoffs(rows: list[dict[str, Any]]) -> dict[str, float]:
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


def detect_patterns(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts = {k: 0 for k in PATTERN_THRESHOLDS}
    cutoffs = recovery_cutoffs(rows)
    for row in rows:
        if not is_enforceable_incident(row):
            continue
        incident_type = str(row.get("type", "")).strip().lower()
        if incident_type not in counts:
            continue
        ts = parse_ts(str(row.get("ts", "")))
        if ts <= cutoffs.get(incident_type, 0.0):
            continue
        counts[incident_type] += 1
    return counts


def detect_trends(rows: list[dict[str, Any]]) -> dict[str, bool]:
    now = time.time()
    recent_start = now - TREND_WINDOW_SECONDS
    prev_start = now - 2 * TREND_WINDOW_SECONDS
    cutoffs = recovery_cutoffs(rows)
    trend: dict[str, bool] = {}
    for incident_type in PATTERN_THRESHOLDS:
        recent = 0
        previous = 0
        for row in rows:
            if not is_enforceable_incident(row):
                continue
            if str(row.get("type", "")).strip().lower() != incident_type:
                continue
            ts = parse_ts(str(row.get("ts", "")))
            if ts <= cutoffs.get(incident_type, 0.0):
                continue
            if ts >= recent_start:
                recent += 1
            elif prev_start <= ts < recent_start:
                previous += 1
        trend[incident_type] = recent > previous and recent >= 2
    return trend


def build_enforced_rules(counts: dict[str, int], trends: dict[str, bool]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    now = time.time()
    created_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now))
    review_by = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now + RULE_REVIEW_HOURS * 3600))
    expires_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now + RULE_EXPIRE_HOURS * 3600))
    for key, threshold in PATTERN_THRESHOLDS.items():
        count = counts.get(key, 0)
        if count >= threshold:
            severity = "block" if count >= threshold + 2 else "restrict"
            out.append(
                {
                    "id": f"auto-{key}-threshold",
                    "incident_type": key,
                    "threshold": threshold,
                    "count": count,
                    "enforce_with": "self_protection_gate",
                    "action": "block_deploy" if severity == "block" else "restrict_deploy",
                    "severity": severity,
                    "created_at": created_at,
                    "review_by": review_by,
                    "expires_at": expires_at,
                    "manual_override_env": "KIRP_RULE_OVERRIDE_IDS",
                    "reason": f"{key} incidents reached threshold",
                }
            )
        if trends.get(key):
            out.append(
                {
                    "id": f"auto-{key}-trend-up",
                    "incident_type": key,
                    "threshold": 2,
                    "count": count,
                    "enforce_with": "self_protection_gate",
                    "action": "warn",
                    "severity": "warn",
                    "created_at": created_at,
                    "review_by": review_by,
                    "expires_at": expires_at,
                    "manual_override_env": "KIRP_RULE_OVERRIDE_IDS",
                    "reason": f"{key} trend increasing",
                }
            )
    return out


def render_rules_md(counts: dict[str, int], trends: dict[str, bool], enforced_rules: list[dict[str, Any]]) -> str:
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    lines = [
        "---",
        "description: Auto-learned drift and incident rules",
        "alwaysApply: false",
        "---",
        "",
        f"# Auto-learned rules (generated {now})",
        "",
        "These rules are generated from repeated incidents.",
        "",
    ]
    has_any = False
    for key, threshold in PATTERN_THRESHOLDS.items():
        count = counts.get(key, 0)
        if count < threshold:
            continue
        has_any = True
        lines.extend([f"## {key}", f"- Repeated {key} incidents detected: {count} (threshold {threshold}).", ""])
    if not has_any:
        lines.extend(["No repeated incident pattern reached threshold.", ""])
    lines.extend(
        [
            "## Trend detection",
            f"- timeout trend up: {trends.get('timeout', False)}",
            f"- auth_failure trend up: {trends.get('auth_failure', False)}",
            f"- fallback_usage trend up: {trends.get('fallback_usage', False)}",
            "",
            "## Enforced Constraints (machine-readable)",
            "```json",
            json.dumps({"generated_at": now, "rules": enforced_rules}, ensure_ascii=True, indent=2),
            "```",
            "",
        ]
    )
    return "\n".join(lines)


def cmd_log(args: argparse.Namespace) -> int:
    meta: dict[str, Any] = {}
    if args.meta:
        try:
            parsed = json.loads(args.meta)
            if isinstance(parsed, dict):
                meta = parsed
        except json.JSONDecodeError:
            pass
    payload = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "type": args.type,
        "source": args.source,
        "message": args.message,
        "commit_sha": args.commit_sha or "unknown",
        "meta": meta,
    }
    append_incident(Path(args.log_path), payload)
    print("incident_memory: logged")
    return 0


def cmd_resolve(args: argparse.Namespace) -> int:
    payload = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "type": "recovery",
        "source": args.source,
        "message": f"recovery marker for {args.target_type}",
        "commit_sha": args.commit_sha or "unknown",
        "meta": {"target_type": args.target_type},
    }
    append_incident(Path(args.log_path), payload)
    print(f"incident_memory: recovery logged for {args.target_type}")
    return 0


def cmd_analyze(args: argparse.Namespace) -> int:
    log_path = Path(args.log_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    if not log_path.exists():
        log_path.write_text("", encoding="utf-8")
    rows = read_incidents(log_path)
    counts = detect_patterns(rows)
    trends = detect_trends(rows)
    enforced_rules = build_enforced_rules(counts, trends)
    text = render_rules_md(counts, trends, enforced_rules)
    rules_path = Path(args.rules_path)
    rules_path.parent.mkdir(parents=True, exist_ok=True)
    rules_path.write_text(text + "\n", encoding="utf-8")
    print(f"incident_memory: analyzed {len(rows)} incidents")
    for key, count in counts.items():
        print(f"{key}: {count}")
    for key, is_up in trends.items():
        print(f"{key}_trend_up: {is_up}")
    print(f"enforced_rules: {len(enforced_rules)}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="command", required=True)

    p_log = sub.add_parser("log")
    p_log.add_argument("--type", required=True)
    p_log.add_argument("--source", required=True)
    p_log.add_argument("--message", required=True)
    p_log.add_argument("--commit-sha", default="")
    p_log.add_argument("--meta", default="")
    p_log.add_argument("--log-path", default=str(DEFAULT_LOG))
    p_log.set_defaults(func=cmd_log)

    p_resolve = sub.add_parser("resolve")
    p_resolve.add_argument("--target-type", required=True)
    p_resolve.add_argument("--source", default="system")
    p_resolve.add_argument("--commit-sha", default="")
    p_resolve.add_argument("--log-path", default=str(DEFAULT_LOG))
    p_resolve.set_defaults(func=cmd_resolve)

    p_an = sub.add_parser("analyze")
    p_an.add_argument("--log-path", default=str(DEFAULT_LOG))
    p_an.add_argument("--rules-path", default=str(DEFAULT_RULES))
    p_an.set_defaults(func=cmd_analyze)

    return p


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
