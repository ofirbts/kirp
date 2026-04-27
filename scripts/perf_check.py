#!/usr/bin/env python3
"""Performance regression gate for KIRP critical flows."""

from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import time
from pathlib import Path
from typing import Any
from urllib.error import URLError, HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


def percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    sorted_values = sorted(values)
    idx = max(0, min(len(sorted_values) - 1, int(round((p / 100.0) * (len(sorted_values) - 1)))))
    return float(sorted_values[idx])


def timed_request(url: str, method: str = "GET", payload: dict[str, Any] | None = None) -> tuple[float, int]:
    data = None
    headers = {"Content-Type": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
    req = Request(url=url, method=method, data=data, headers=headers)
    started = time.perf_counter()
    try:
        with urlopen(req, timeout=15) as resp:
            _ = resp.read()
            status = int(resp.status)
    except HTTPError as e:
        status = int(e.code)
    except URLError as e:
        raise RuntimeError(f"network_error: {e}") from e
    elapsed_ms = (time.perf_counter() - started) * 1000.0
    return elapsed_ms, status


def measure_flow(url: str, samples: int, method: str = "GET", payload: dict[str, Any] | None = None) -> dict[str, Any]:
    durations: list[float] = []
    failures = 0
    for _ in range(samples):
        d_ms, status = timed_request(url, method=method, payload=payload)
        durations.append(d_ms)
        if status >= 400:
            failures += 1
    return {
        "p50_ms": round(statistics.median(durations), 1) if durations else 0.0,
        "p95_ms": round(percentile(durations, 95), 1),
        "failures": failures,
    }


def evaluate(
    flow: str,
    measured_p95: float,
    baseline_p95: float,
    absolute_max: float,
    regression_ratio_max: float,
) -> tuple[str, str]:
    if measured_p95 > absolute_max:
        return "fail", f"absolute threshold exceeded ({measured_p95:.1f} > {absolute_max:.1f})"
    if measured_p95 > baseline_p95 * regression_ratio_max:
        return "fail", (
            f"relative regression exceeded ({measured_p95:.1f} > "
            f"{baseline_p95 * regression_ratio_max:.1f})"
        )
    return "pass", "within thresholds"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", default="docs/perf-baseline.json")
    parser.add_argument("--samples-dashboard", type=int, default=40)
    parser.add_argument("--samples-ask", type=int, default=25)
    parser.add_argument("--samples-next-action", type=int, default=25)
    parser.add_argument("--api-base", default=os.getenv("KIRP_API_BASE", "http://localhost:8000"))
    parser.add_argument("--dashboard-base", default=os.getenv("KIRP_DASHBOARD_BASE", "http://localhost:3100"))
    args = parser.parse_args()

    baseline = json.loads(Path(args.baseline).read_text())
    thresholds = baseline["thresholds"]
    baseline_p95 = baseline["baseline_p95_ms"]
    ratio = float(baseline["regression_ratio_max"])

    try:
        results = {
            "dashboard_load": measure_flow(
                f"{args.dashboard_base.rstrip('/')}/dashboard",
                args.samples_dashboard,
                "GET",
            ),
            "ask": measure_flow(
                f"{args.api_base.rstrip('/')}/api/v1/ask",
                args.samples_ask,
                "POST",
                {"query": "performance probe"},
            ),
            "next_action_proxy": measure_flow(
                f"{args.api_base.rstrip('/')}/api/v1/tasks?{urlencode({'tenant_id': 'default', 'space_id': 'all'})}",
                args.samples_next_action,
                "POST",
                {"title": "perf probe task"},
            ),
        }
    except Exception as e:
        print(f"perf check execution error: {e}")
        return 2

    status = 0
    flows = {}
    checks = {
        "dashboard_load": thresholds["dashboard_load_p95_ms_max"],
        "ask": thresholds["ask_p95_ms_max"],
        "next_action_proxy": thresholds["next_action_proxy_p95_ms_max"],
    }
    for flow, data in results.items():
        flow_status, reason = evaluate(
            flow=flow,
            measured_p95=float(data["p95_ms"]),
            baseline_p95=float(baseline_p95[flow]),
            absolute_max=float(checks[flow]),
            regression_ratio_max=ratio,
        )
        if flow_status != "pass":
            status = 1
        flows[flow] = {
            "p50_ms": data["p50_ms"],
            "p95_ms": data["p95_ms"],
            "status": flow_status,
            "reason": reason,
        }
        print(f"{flow}: {flow_status} ({reason}) p95={data['p95_ms']}ms")

    payload = {
        "env": baseline.get("env", "unknown"),
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "flows": flows,
    }
    out_dir = Path("artifacts/perf")
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "latest-results.json").write_text(json.dumps(payload, indent=2))
    summary_lines = ["# Perf Check Summary", ""]
    for flow, data in flows.items():
        summary_lines.append(
            f"- {flow}: {data['status']} · p95={data['p95_ms']}ms · {data['reason']}"
        )
    (out_dir / "latest-summary.md").write_text("\n".join(summary_lines) + "\n")
    return status


if __name__ == "__main__":
    raise SystemExit(main())
