from __future__ import annotations

import subprocess
from pathlib import Path

import pytest


def test_operational_readiness_script_exists() -> None:
    root = Path(__file__).resolve().parents[1]
    script = root / "scripts" / "operational_readiness_smoke.sh"
    assert script.is_file()
    text = script.read_text(encoding="utf-8")
    assert "tenant_isolation_gate.py" in text
    assert "shadow_pilot_smoke.sh" in text
    assert "staging_tenant_smoke.sh" in text
    assert "SKIP_AUTH=0" in text
    assert "STAGING_SMOKE_POLL_SEC" in text
    assert 'STAGING_SMOKE_POLL_SEC:-180}' in text
    assert "127.0.0.1:8000" in text


def test_smoke_scripts_default_api_port_8000() -> None:
    root = Path(__file__).resolve().parents[1]
    for name in (
        "staging_tenant_smoke.sh",
        "telemetry_smoke.sh",
        "shadow_pilot_smoke.sh",
        "operational_readiness_smoke.sh",
    ):
        text = (root / "scripts" / name).read_text(encoding="utf-8")
        assert "127.0.0.1:8000" in text
        assert "127.0.0.1:8002" not in text


def test_shadow_pilot_smoke_live() -> None:
    root = Path(__file__).resolve().parents[1]
    api = None
    for port in (8000, 8002):
        candidate = f"http://127.0.0.1:{port}"
        probe = subprocess.run(
            ["curl", "-sS", "-o", "/dev/null", "-w", "%{http_code}", f"{candidate}/health"],
            capture_output=True,
            text=True,
            check=False,
        )
        if probe.stdout.strip() == "200":
            api = candidate
            break
    if api is None:
        pytest.skip("KIRP API not running on 127.0.0.1:8000 or :8002")
    proc = subprocess.run(
        ["bash", "scripts/shadow_pilot_smoke.sh"],
        cwd=root,
        env={"KIRP_API_URL": api, "PATH": "/usr/bin:/bin"},
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "ALL PASSED" in proc.stdout
