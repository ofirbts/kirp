from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_TENANT_TS = _ROOT / "lib" / "effectiveTenant.ts"


def test_effective_tenant_no_implicit_dev_skip_auth() -> None:
    text = _TENANT_TS.read_text(encoding="utf-8")
    fn_block = text.split("function isSkipAuthClientMode")[1].split("export function resolveTenantForApi")[0]
    assert "development" not in fn_block
    assert "local" not in fn_block
    assert "NEXT_PUBLIC_SKIP_AUTH" in fn_block


def test_effective_tenant_rejects_missing_without_skip_auth() -> None:
    script = """
const explicit = ("").trim();
if (explicit) process.exit(2);
const skip = process.env.NEXT_PUBLIC_SKIP_AUTH === "1";
if (skip) process.exit(3);
throw new Error("tenant_id required — sign in or set tenant context");
"""
    env = os.environ.copy()
    env["NEXT_PUBLIC_SKIP_AUTH"] = "0"
    env["NODE_ENV"] = "development"
    proc = subprocess.run(
        ["node", "-e", script],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode != 0
    assert "tenant_id required" in (proc.stderr or proc.stdout or "")


def test_effective_tenant_resolve_allows_explicit_skip_auth_default() -> None:
    text = _TENANT_TS.read_text(encoding="utf-8")
    assert re.search(
        r'if \(isSkipAuthClientMode\(\)\) return DEFAULT_TENANT_ID',
        text,
    )
