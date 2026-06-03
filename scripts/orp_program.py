#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PROGRAM_FILE = ROOT / "scripts" / "operational_readiness_program.json"
ARTIFACTS = ROOT / "artifacts" / "operational_readiness"
START_FILE = ARTIFACTS / "program_start.txt"


def load_program() -> dict[str, Any]:
    return json.loads(PROGRAM_FILE.read_text(encoding="utf-8"))


def program_day_number(start: date, today: date | None = None) -> int:
    ref = today or date.today()
    delta = (ref - start).days + 1
    return max(1, min(delta, int(load_program()["duration_days"])))


def init_program(force: bool = False) -> int:
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    if START_FILE.exists() and not force:
        start = START_FILE.read_text(encoding="utf-8").strip()
        print(f"program already started: {start}")
        print(f"current day: {program_day_number(date.fromisoformat(start))}")
        return 0
    today = date.today().isoformat()
    START_FILE.write_text(today + "\n", encoding="utf-8")
    print(f"program_start: {today}")
    print(f"day 1 begins today; run: ./scripts/orp_daily.sh")
    return 0


def run_cmd(cmd: list[str], *, env: dict[str, str] | None = None) -> dict[str, Any]:
    merged = os.environ.copy()
    if env:
        merged.update(env)
    proc = subprocess.run(
        cmd,
        cwd=ROOT,
        env=merged,
        capture_output=True,
        text=True,
        check=False,
    )
    return {
        "command": cmd,
        "exit_code": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "passed": proc.returncode == 0,
    }


def fetch_health(api: str) -> dict[str, Any]:
    url = f"{api.rstrip('/')}/health"
    try:
        with urllib.request.urlopen(url, timeout=20) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        return {"error": str(exc), "status": "unreachable"}


def write_evidence(day: int, payload: dict[str, Any]) -> Path:
    day_dir = ARTIFACTS / f"day-{day:02d}"
    day_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = day_dir / f"evidence-{stamp}.json"
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    latest = day_dir / "latest.json"
    latest.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
    return path


def consumer_hint() -> str | None:
    from scripts.staging_tenant_helpers import kafka_consumer_hint

    return kafka_consumer_hint()


def latency_run(api: str, samples: int) -> dict[str, Any]:
    from scripts.staging_tenant_helpers import create_smoke_token
    from scripts.orp_latency import (
        default_poll_timeout,
        evaluate_latency_threshold,
        measure_ingest_latency,
    )

    token = create_smoke_token("user_a", "tenant_a")
    report = measure_ingest_latency(
        api,
        token,
        samples=samples,
        poll_timeout_sec=default_poll_timeout(),
    )
    staging_url = (os.getenv("KIRP_STAGING_API_URL") or "").strip()
    is_staging = bool(staging_url) and api.rstrip("/") == staging_url.rstrip("/")
    program = load_program()
    rules = program["go_no_go"]
    report["threshold"] = evaluate_latency_threshold(
        report,
        is_staging=is_staging,
        max_local_p95=float(rules["max_latency_p95_sec_local"]),
        max_staging_p95=float(rules["max_latency_p95_sec_staging"]),
    )
    return report


def run_day(day: int, *, api: str) -> int:
    program = load_program()
    day_spec = next(d for d in program["days"] if d["day"] == day)
    checks: list[dict[str, Any]] = []
    fail = 0

    def record(check_id: str, result: dict[str, Any]) -> None:
        nonlocal fail
        if not result.get("passed", False):
            fail = 1
        checks.append({"id": check_id, **result})

    env_base = {
        "KIRP_API_URL": api,
        "SKIP_AUTH": "0",
        "STAGING_SMOKE_POLL_SEC": os.getenv("STAGING_SMOKE_POLL_SEC", "180"),
    }

    hint = consumer_hint()
    if hint:
        checks.append({"id": "consumer_preflight", "passed": False, "warning": hint})
        if day <= 2 or day == 6:
            fail = 1

    if day == 1:
        record("ci_local", run_cmd(["bash", "scripts/ci_local.sh"], env=env_base))
        record(
            "operational_readiness",
            run_cmd(["bash", "scripts/operational_readiness_smoke.sh"], env=env_base),
        )
        health = fetch_health(api)
        checks.append({"id": "health_snapshot", "passed": health.get("status") == "healthy", "data": health})
        if health.get("status") != "healthy":
            fail = 1
        lat = latency_run(api, 3)
        checks.append(
            {
                "id": "latency_samples",
                "passed": lat["summary"]["samples_success"] >= 1,
                "data": lat,
            }
        )
        if lat["summary"]["samples_success"] < 1:
            fail = 1

    elif day == 2:
        record("tenant_isolation_gate", run_cmd(["python3", "scripts/tenant_isolation_gate.py"]))
        for i in (1, 2):
            record(
                f"staging_tenant_smoke_{i}",
                run_cmd(["bash", "scripts/staging_tenant_smoke.sh"], env=env_base),
            )

    elif day == 3:
        record("telemetry_smoke", run_cmd(["bash", "scripts/telemetry_smoke.sh"], env=env_base))
        record("shadow_pilot_smoke", run_cmd(["bash", "scripts/shadow_pilot_smoke.sh"], env=env_base))
        health = fetch_health(api)
        telemetry = health.get("telemetry") or {}
        ok = (
            health.get("status") == "healthy"
            and telemetry.get("ok") is True
            and (telemetry.get("governed_runtime_mode") == "shadow")
        )
        checks.append({"id": "trace_health_fields", "passed": ok, "data": telemetry})
        if not ok:
            fail = 1

    elif day == 4:
        staging = (os.getenv("KIRP_STAGING_API_URL") or "").strip()
        target = staging or api
        staging_env = {**env_base, "KIRP_API_URL": target}
        result = run_cmd(["bash", "scripts/operational_readiness_smoke.sh"], env=staging_env)
        record("staging_or_local_readiness", result)
        checks.append(
            {
                "id": "staging_target",
                "passed": True,
                "target": target,
                "staging_configured": bool(staging),
                "staging_skipped": not bool(staging),
            }
        )
        checks.append({"id": "auth_mode", "passed": True, "skip_auth": "0"})

    elif day == 5:
        lat = latency_run(api, 10)
        thr = lat.get("threshold") or {}
        checks.append({"id": "latency_benchmark", "passed": bool(thr.get("passed")), "data": lat})
        if not thr.get("passed"):
            fail = 1

    elif day == 6:
        for i in (1, 2, 3):
            record(
                f"soak_run_{i}",
                run_cmd(["bash", "scripts/operational_readiness_smoke.sh"], env=env_base),
            )

    elif day == 7:
        record(
            "final_operational_readiness",
            run_cmd(["bash", "scripts/operational_readiness_smoke.sh"], env=env_base),
        )
        verdict = evaluate_go_no_go(write_verdict_file=False)
        checks.append({"id": "go_no_go_preview", "passed": verdict["verdict"] == "GO", "data": verdict})
        if verdict["verdict"] != "GO":
            fail = 1

    else:
        print(f"unknown day: {day}", file=sys.stderr)
        return 2

    payload = {
        "program_version": program["version"],
        "day": day,
        "title": day_spec["title"],
        "focus": day_spec["focus"],
        "date": date.today().isoformat(),
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "api_url": api,
        "consumer_hint": hint,
        "checklist": day_spec["checklist"],
        "evidence_required": day_spec["evidence_required"],
        "acceptance_criteria": day_spec["acceptance_criteria"],
        "checks": checks,
        "overall": "pass" if fail == 0 else "fail",
    }
    path = write_evidence(day, payload)
    print(f"=== ORP Day {day}: {day_spec['title']} ===")
    print(f"overall: {payload['overall'].upper()}")
    try:
        rel = path.relative_to(ROOT)
    except ValueError:
        rel = path
    print(f"evidence: {rel}")
    if hint:
        print(f"WARN: {hint}")
    return fail


def list_day_evidence() -> dict[int, dict[str, Any]]:
    out: dict[int, dict[str, Any]] = {}
    if not ARTIFACTS.exists():
        return out
    for day_dir in sorted(ARTIFACTS.glob("day-*")):
        latest = day_dir / "latest.json"
        if not latest.is_file():
            continue
        data = json.loads(latest.read_text(encoding="utf-8"))
        day = int(data.get("day", 0))
        out[day] = data
    return out


def evaluate_go_no_go(*, write_verdict_file: bool = True) -> dict[str, Any]:
    program = load_program()
    rules = program["go_no_go"]
    days = list_day_evidence()
    blockers: list[str] = []
    duration = int(program["duration_days"])

    passed_days = [d for d, ev in days.items() if ev.get("overall") == "pass"]
    for d in range(1, duration + 1):
        if d not in days:
            blockers.append(f"missing_evidence_day_{d}")
        elif days[d].get("overall") != "pass":
            blockers.append(f"day_{d}_overall_fail")

    if len(passed_days) < int(rules["min_days_passed"]):
        blockers.append(
            f"insufficient_pass_days:{len(passed_days)}<{rules['min_days_passed']}"
        )

    staging_url = (os.getenv("KIRP_STAGING_API_URL") or "").strip()
    if staging_url and rules.get("require_staging_when_url_set"):
        day4 = days.get(4)
        if not day4 or day4.get("overall") != "pass":
            blockers.append("staging_day_4_not_passed")
        else:
            target = None
            for c in day4.get("checks", []):
                if c.get("id") == "staging_target":
                    target = c.get("target")
            if target and target.rstrip("/") != staging_url.rstrip("/"):
                blockers.append("staging_day_4_not_against_staging_url")

    consumer_days = [
        d
        for d, ev in days.items()
        if ev.get("consumer_hint")
    ]
    if len(consumer_days) > int(rules["max_unresolved_consumer_hint_days"]):
        blockers.append(f"consumer_hint_on_days:{consumer_days}")

    for d, ev in days.items():
        for check in ev.get("checks", []):
            if check.get("id") == "health_snapshot":
                mode = ((check.get("data") or {}).get("telemetry") or {}).get(
                    "governed_runtime_mode"
                )
                if mode != rules["required_governed_runtime_mode"]:
                    blockers.append(f"day_{d}_governed_mode_{mode}")

    day5 = days.get(5)
    if day5:
        for check in day5.get("checks", []):
            if check.get("id") == "latency_benchmark" and not check.get("passed"):
                blockers.append("day_5_latency_threshold_failed")
    else:
        blockers.append("missing_day_5_latency")

    verdict = "GO" if not blockers else "NO-GO"
    result = {
        "verdict": verdict,
        "program_version": program["version"],
        "evaluated_at_utc": datetime.now(timezone.utc).isoformat(),
        "days_with_evidence": sorted(days.keys()),
        "days_passed": sorted(passed_days),
        "blockers": blockers,
        "go_no_go_rules": rules,
        "recommendation": (
            "Approve KIRP_GOVERNED_RUNTIME_MODE=enforce only after explicit human signoff."
            if verdict == "GO"
            else "Remain in shadow; resolve blockers and re-run daily program."
        ),
        "enforce_transition_requires_explicit_approval": rules.get(
            "enforce_transition_requires_explicit_approval", True
        ),
    }
    if write_verdict_file:
        ARTIFACTS.mkdir(parents=True, exist_ok=True)
        out = ARTIFACTS / "go_no_go_verdict.json"
        out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        index = {
            "days": {
                str(d): str((ARTIFACTS / f"day-{d:02d}" / "latest.json").relative_to(ROOT))
                for d in sorted(days.keys())
            },
            "verdict": str(out.relative_to(ROOT)),
        }
        (ARTIFACTS / "evidence_index.json").write_text(
            json.dumps(index, indent=2) + "\n", encoding="utf-8"
        )
    return result


def print_status() -> int:
    program = load_program()
    if not START_FILE.is_file():
        print("program not started; run: ./scripts/orp_init.sh")
        return 0
    start = date.fromisoformat(START_FILE.read_text(encoding="utf-8").strip())
    today_day = program_day_number(start)
    days = list_day_evidence()
    print(f"program_start: {start.isoformat()}")
    print(f"calendar_day: {today_day} / {program['duration_days']}")
    for d in range(1, program["duration_days"] + 1):
        spec = next(x for x in program["days"] if x["day"] == d)
        if d in days:
            status = days[d].get("overall", "?").upper()
        else:
            status = "PENDING"
        mark = ">" if d == today_day else " "
        print(f"{mark} Day {d}: {status} — {spec['title']}")
    if len(days) >= program["duration_days"]:
        verdict = evaluate_go_no_go()
        print(f"go_no_go: {verdict['verdict']}")
        if verdict["blockers"]:
            for b in verdict["blockers"]:
                print(f"  blocker: {b}")
    return 0


def print_day_plan(day: int) -> int:
    program = load_program()
    spec = next(d for d in program["days"] if d["day"] == day)
    print(f"=== Day {day}: {spec['title']} ({spec['focus']}) ===")
    print("Checklist:")
    for item in spec["checklist"]:
        print(f"  - {item}")
    print("Evidence required:")
    for item in spec["evidence_required"]:
        print(f"  - {item}")
    print("Acceptance criteria:")
    for item in spec["acceptance_criteria"]:
        print(f"  - {item}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="KIRP 7-day Operational Readiness Program")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_init = sub.add_parser("init", help="Start 7-day program clock")
    p_init.add_argument("--force", action="store_true", help="Reset program start date")

    p_daily = sub.add_parser("daily", help="Run today's program day")
    p_daily.add_argument("--day", type=int, help="Override day number (1-7)")
    p_daily.add_argument("--api", default=os.getenv("KIRP_API_URL", "http://127.0.0.1:8000"))

    sub.add_parser("status", help="Show program progress")
    sub.add_parser("go-no-go", help="Evaluate shadow→enforce gate")
    p_plan = sub.add_parser("plan", help="Print checklist for a day")
    p_plan.add_argument("--day", type=int, required=True)

    args = parser.parse_args(argv)

    if args.cmd == "init":
        return init_program(force=bool(getattr(args, "force", False)))
    if args.cmd == "status":
        return print_status()
    if args.cmd == "go-no-go":
        result = evaluate_go_no_go()
        print(json.dumps(result, indent=2))
        return 0 if result["verdict"] == "GO" else 1
    if args.cmd == "plan":
        return print_day_plan(args.day)
    if args.cmd == "daily":
        if not START_FILE.is_file():
            print("run ./scripts/orp_init.sh first", file=sys.stderr)
            return 2
        start = date.fromisoformat(START_FILE.read_text(encoding="utf-8").strip())
        day = args.day if args.day is not None else program_day_number(start)
        return run_day(day, api=args.api)

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
