#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import re
import subprocess
import sys


def log_incident(message: str) -> None:
    try:
        subprocess.run(
            [
                sys.executable,
                "scripts/incident_memory.py",
                "log",
                "--type",
                "auth_failure",
                "--source",
                "auth_consistency_check",
                "--message",
                message,
            ],
            check=False,
            capture_output=True,
            text=True,
        )
    except Exception:
        pass


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    backend_file = root / "src" / "main.py"
    frontend_file = root / "lib" / "stores" / "authStore.ts"
    prod_env_example = root / "deploy" / ".env.prod.example"

    if not backend_file.exists() or not frontend_file.exists() or not prod_env_example.exists():
        print("auth_consistency_check: required files missing")
        log_incident("required auth consistency files missing")
        return 2

    backend_text = backend_file.read_text(encoding="utf-8")
    frontend_text = frontend_file.read_text(encoding="utf-8")
    prod_env_text = prod_env_example.read_text(encoding="utf-8")

    if 'os.getenv("SKIP_AUTH"' not in backend_text:
        print("auth_consistency_check: backend SKIP_AUTH guard missing")
        log_incident("backend SKIP_AUTH guard missing")
        return 3
    if "process.env.NEXT_PUBLIC_SKIP_AUTH" not in frontend_text:
        print("auth_consistency_check: frontend NEXT_PUBLIC_SKIP_AUTH guard missing")
        log_incident("frontend NEXT_PUBLIC_SKIP_AUTH guard missing")
        return 4

    enabled_prod_skip_auth = re.search(r"^\s*SKIP_AUTH\s*=\s*1\s*$", prod_env_text, flags=re.MULTILINE)
    if enabled_prod_skip_auth:
        print("auth_consistency_check: SKIP_AUTH=1 must not be enabled in deploy/.env.prod.example")
        log_incident("SKIP_AUTH=1 enabled in deploy/.env.prod.example")
        return 5

    print("auth_consistency_check: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
