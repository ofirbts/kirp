from __future__ import annotations

import json
import os
import statistics
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class LatencySample:
    marker: str
    ingest_http: int
    seconds_to_marker: float | None
    success: bool
    error: str | None = None


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = max(0, min(len(ordered) - 1, int(round((pct / 100.0) * (len(ordered) - 1)))))
    return ordered[idx]


def measure_ingest_latency(
    api_base: str,
    token: str,
    *,
    samples: int = 3,
    poll_timeout_sec: int = 180,
    prefix: str = "orp-latency",
) -> dict[str, Any]:
    from scripts.staging_tenant_helpers import (
        events_json_contains_marker,
        fetch_events,
        poll_events_for_marker,
    )

    api = api_base.rstrip("/")
    ingest_url = f"{api}/api/v1/ingest"
    results: list[LatencySample] = []

    for i in range(samples):
        marker = f"{prefix}-{int(time.time())}-{i}"
        body = json.dumps({"content": marker, "source": "orp_latency"}).encode("utf-8")
        req = urllib.request.Request(
            ingest_url,
            data=body,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        ingest_http = 0
        err: str | None = None
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                ingest_http = resp.status
        except urllib.error.HTTPError as exc:
            ingest_http = exc.code
            err = exc.read().decode("utf-8", errors="replace")[:500]
        except (TimeoutError, urllib.error.URLError, OSError) as exc:
            err = str(exc)

        if ingest_http != 200:
            results.append(
                LatencySample(marker, ingest_http, None, False, err)
            )
            if i + 1 < samples:
                time.sleep(1.0)
            continue

        start = time.time()
        ok = poll_events_for_marker(
            api,
            token,
            marker,
            timeout_sec=poll_timeout_sec,
            interval_sec=2.0,
        )
        elapsed = time.time() - start
        if not ok:
            status, blob = fetch_events(api, token)
            found = status == 200 and events_json_contains_marker(blob, marker)
            ok = found
        results.append(
            LatencySample(
                marker,
                ingest_http,
                round(elapsed, 2) if ok else None,
                ok,
                None if ok else "marker not found within poll timeout",
            )
        )
        if i + 1 < samples:
            time.sleep(2.0)

    successes = [s.seconds_to_marker for s in results if s.success and s.seconds_to_marker is not None]
    summary = {
        "samples_requested": samples,
        "samples_success": len(successes),
        "samples_failed": len(results) - len(successes),
        "p50_sec": round(statistics.median(successes), 2) if successes else None,
        "p95_sec": round(_percentile(successes, 95), 2) if successes else None,
        "max_sec": round(max(successes), 2) if successes else None,
        "min_sec": round(min(successes), 2) if successes else None,
    }
    return {
        "api": api,
        "poll_timeout_sec": poll_timeout_sec,
        "summary": summary,
        "samples": [asdict(s) for s in results],
    }


def evaluate_latency_threshold(
    latency_report: dict[str, Any],
    *,
    is_staging: bool,
    max_local_p95: float,
    max_staging_p95: float,
) -> dict[str, Any]:
    p95 = (latency_report.get("summary") or {}).get("p95_sec")
    threshold = max_staging_p95 if is_staging else max_local_p95
    passed = p95 is not None and float(p95) <= threshold
    return {
        "is_staging": is_staging,
        "p95_sec": p95,
        "threshold_sec": threshold,
        "passed": passed,
    }


def default_api_url() -> str:
    return (os.getenv("KIRP_API_URL") or "http://127.0.0.1:8000").strip()


def default_poll_timeout() -> int:
    return int(os.getenv("STAGING_SMOKE_POLL_SEC", "180"))
