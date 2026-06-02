#!/usr/bin/env python3
"""Browser-level user-perceived latency gate for monitoring Next Action."""

from __future__ import annotations

import argparse
import json
import os
import statistics
import subprocess
import sys
import time
from pathlib import Path

def write_fail_artifact(commit_sha: str, reason: str) -> None:
    out_dir = Path("artifacts/perf")
    out_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "commit_sha": commit_sha,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "status": "fail",
        "results": {},
        "checks": {
            "ux_runtime": {
                "status": "fail",
                "reason": reason,
            }
        },
    }
    (out_dir / "user-perceived-results.json").write_text(
        json.dumps(payload, indent=2),
        encoding="utf-8",
    )


def percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    idx = max(0, min(len(s) - 1, int(round((p / 100.0) * (len(s) - 1)))))
    return float(s[idx])


def evaluate(measured: float, baseline: float, absolute_max: float, ratio_max: float) -> tuple[str, str]:
    if measured > absolute_max:
        return "fail", f"absolute threshold exceeded ({measured:.1f} > {absolute_max:.1f})"
    if measured > baseline * ratio_max:
        return "fail", f"relative regression exceeded ({measured:.1f} > {(baseline * ratio_max):.1f})"
    return "pass", "within thresholds"


def log_incident(incident_type: str, source: str, message: str, commit_sha: str) -> None:
    try:
        subprocess.run(
            [
                sys.executable,
                "scripts/incident_memory.py",
                "log",
                "--type",
                incident_type,
                "--source",
                source,
                "--message",
                message,
                "--commit-sha",
                commit_sha,
            ],
            check=False,
            capture_output=True,
            text=True,
        )
    except Exception:
        pass


def ensure_playwright_installed() -> tuple[bool, str]:
    try:
        from playwright.sync_api import sync_playwright  # noqa: F401
        return True, "playwright already installed"
    except Exception:
        pass
    try:
        pip_cmd = [sys.executable, "-m", "pip", "install", "playwright"]
        install_cmd = [sys.executable, "-m", "playwright", "install", "chromium"]
        p1 = subprocess.run(pip_cmd, check=False, capture_output=True, text=True)
        p2 = subprocess.run(install_cmd, check=False, capture_output=True, text=True)
        if p1.returncode == 0 and p2.returncode == 0:
            return True, "playwright installed automatically"
        return (
            False,
            "failed auto-install. Run: "
            f"{sys.executable} -m pip install playwright && "
            f"{sys.executable} -m playwright install chromium",
        )
    except Exception as e:
        return (
            False,
            "failed auto-install due to exception. Run: "
            f"{sys.executable} -m pip install playwright && "
            f"{sys.executable} -m playwright install chromium "
            f"(error: {e})",
        )


def measure_once(page, url: str) -> tuple[float, float]:
    start = time.perf_counter()
    page.goto(url, wait_until="domcontentloaded", timeout=20_000)
    page.wait_for_selector("text=Next Action", timeout=20_000)
    load_ms = (time.perf_counter() - start) * 1000.0

    button = page.locator(
        "button:has-text('Create tracked task'),"
        "button:has-text('Open run'),"
        "button:has-text('Start something focused')"
    ).first
    click_started = time.perf_counter()
    button.evaluate("el => el.click()")
    page.wait_for_function(
        """
        () => {
          const hasState = Boolean(document.querySelector('[data-result-state]'));
          const applyingBtn = Array.from(document.querySelectorAll('button')).some(
            (b) => (b.textContent || '').includes('Applying')
          );
          return hasState || applyingBtn;
        }
        """,
        timeout=12_000,
    )
    confirmation_ms = (time.perf_counter() - click_started) * 1000.0
    return load_ms, confirmation_ms


def bootstrap_auth_token(page, api_base: str) -> None:
    email = os.getenv("KIRP_UX_EMAIL", "e2e-user@example.com").strip()
    password = os.getenv("KIRP_UX_PASSWORD", "e2e-password-123").strip()
    name = os.getenv("KIRP_UX_NAME", "UX E2E")
    token = None
    login = page.request.post(
        f"{api_base.rstrip('/')}/api/v1/auth/login",
        data={"email": email, "password": password},
        timeout=20_000,
    )
    if login.ok:
        token = (login.json() or {}).get("access_token")
    else:
        signup = page.request.post(
            f"{api_base.rstrip('/')}/api/v1/auth/signup",
            data={"email": email, "password": password, "name": name},
            timeout=20_000,
        )
        if signup.ok:
            token = (signup.json() or {}).get("access_token")
        else:
            retry_login = page.request.post(
                f"{api_base.rstrip('/')}/api/v1/auth/login",
                data={"email": email, "password": password},
                timeout=20_000,
            )
            if retry_login.ok:
                token = (retry_login.json() or {}).get("access_token")
    if not token:
        raise RuntimeError("could not bootstrap auth token for UX browser flow")
    token_literal = json.dumps(str(token))
    page.add_init_script(
        script=(
            "window.localStorage.setItem('access_token', "
            + token_literal
            + ");"
            "window.localStorage.setItem('kirp_auth_token', "
            + token_literal
            + ");"
            "window.sessionStorage.setItem('access_token', "
            + token_literal
            + ");"
        )
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", default="docs/user-perceived-baseline.json")
    parser.add_argument("--dashboard-url", default=os.getenv("KIRP_DASHBOARD_BASE", "http://localhost:3100") + "/monitoring?tenant=default")
    parser.add_argument("--api-base", default=os.getenv("KIRP_API_BASE", "http://localhost:8000"))
    parser.add_argument("--samples", type=int, default=7)
    parser.add_argument("--commit-sha", default=os.getenv("GITHUB_SHA", "unknown"))
    args = parser.parse_args()

    baseline = json.loads(Path(args.baseline).read_text(encoding="utf-8"))
    thresholds = baseline["thresholds"]
    baseline_p95 = baseline["baseline_p95_ms"]
    ratio = float(baseline.get("regression_ratio_max", 1.2))

    ok, setup_message = ensure_playwright_installed()
    if not ok:
        print(f"ux_reality_check: playwright unavailable: {setup_message}")
        log_incident(
            "fallback_usage",
            "ux_reality_check",
            f"playwright unavailable: {setup_message}",
            args.commit_sha,
        )
        write_fail_artifact(args.commit_sha, f"playwright unavailable: {setup_message}")
        return 2
    try:
        from playwright.sync_api import sync_playwright
    except Exception as e:
        print(
            "ux_reality_check: playwright import failed after setup. "
            f"Remediation: {sys.executable} -m pip install playwright && "
            f"{sys.executable} -m playwright install chromium. Details: {e}"
        )
        log_incident("fallback_usage", "ux_reality_check", f"playwright import failed: {e}", args.commit_sha)
        write_fail_artifact(args.commit_sha, f"playwright import failed: {e}")
        return 2

    load_samples: list[float] = []
    confirm_samples: list[float] = []
    errors = 0

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        try:
            bootstrap_auth_token(page, args.api_base)
        except Exception as e:
            print(f"ux_reality_check: auth bootstrap failed: {e}")
            log_incident("fallback_usage", "ux_reality_check", f"auth bootstrap failed: {e}", args.commit_sha)
            write_fail_artifact(args.commit_sha, f"auth bootstrap failed: {e}")
            context.close()
            browser.close()
            return 2
        for _ in range(args.samples):
            try:
                load_ms, confirm_ms = measure_once(page, args.dashboard_url)
                load_samples.append(load_ms)
                confirm_samples.append(confirm_ms)
            except Exception:
                errors += 1
                log_incident("fallback_usage", "ux_reality_check", "sample failed while waiting for visible confirmation", args.commit_sha)
        context.close()
        browser.close()

    if not load_samples or not confirm_samples:
        print("ux_reality_check: no successful samples")
        log_incident("fallback_usage", "ux_reality_check", "no successful browser-level samples", args.commit_sha)
        write_fail_artifact(args.commit_sha, "no successful browser-level samples")
        return 2

    results = {
        "click_to_ui_update": {
            "p50_ms": round(statistics.median(load_samples), 1),
            "p95_ms": round(percentile(load_samples, 95), 1),
            "samples_ok": len(load_samples),
            "samples_error": errors,
        },
        "next_action_to_confirmation": {
            "p50_ms": round(statistics.median(confirm_samples), 1),
            "p95_ms": round(percentile(confirm_samples, 95), 1),
            "samples_ok": len(confirm_samples),
            "samples_error": errors,
        },
    }

    checks = {
        "click_to_ui_update": evaluate(
            float(results["click_to_ui_update"]["p95_ms"]),
            float(baseline_p95["click_to_ui_update"]),
            float(thresholds["click_to_ui_update_p95_ms_max"]),
            ratio,
        ),
        "next_action_to_confirmation": evaluate(
            float(results["next_action_to_confirmation"]["p95_ms"]),
            float(baseline_p95["next_action_to_confirmation"]),
            float(thresholds["next_action_to_confirmation_p95_ms_max"]),
            ratio,
        ),
    }

    status = 0
    for flow, (state, reason) in checks.items():
        if state != "pass":
            status = 1
            log_incident("timeout", "ux_reality_check", f"{flow}: {reason}", args.commit_sha)
        print(f"{flow}: {state} ({reason}) p95={results[flow]['p95_ms']}ms")

    payload = {
        "commit_sha": args.commit_sha,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "status": "fail" if status else "pass",
        "results": results,
        "checks": {k: {"status": v[0], "reason": v[1]} for k, v in checks.items()},
    }
    out_dir = Path("artifacts/perf")
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "user-perceived-results.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return status


if __name__ == "__main__":
    raise SystemExit(main())
