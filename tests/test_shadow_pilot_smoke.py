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


def test_shadow_pilot_smoke_live() -> None:
    root = Path(__file__).resolve().parents[1]
    api = "http://127.0.0.1:8002"
    probe = subprocess.run(
        ["curl", "-sS", "-o", "/dev/null", "-w", "%{http_code}", f"{api}/health"],
        capture_output=True,
        text=True,
        check=False,
    )
    if probe.stdout.strip() != "200":
        pytest.skip("API not running on 127.0.0.1:8002")
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
