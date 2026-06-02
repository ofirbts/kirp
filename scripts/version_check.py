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
                "version_mismatch",
                "--source",
                "version_check",
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
    main_py = root / "src" / "main.py"
    health_test = root / "tests" / "test_health_versioning.py"

    if not main_py.exists():
        print("version_check: missing src/main.py")
        log_incident("missing src/main.py")
        return 2
    if not health_test.exists():
        print("version_check: missing tests/test_health_versioning.py")
        log_incident("missing tests/test_health_versioning.py")
        return 3

    text = main_py.read_text(encoding="utf-8")
    required_patterns = [
        r'APP_GIT_SHA\s*=\s*\(os\.getenv\("APP_GIT_SHA"\)\s*or\s*"unknown"\)',
        r'response\.headers\["X-KIRP-Version"\]\s*=\s*APP_GIT_SHA',
        r'"source":\s*"env:APP_GIT_SHA"',
    ]
    missing = [p for p in required_patterns if re.search(p, text) is None]
    if missing:
        print("version_check: required version contract markers missing")
        for p in missing:
            print(p)
        log_incident("required version contract markers missing")
        return 4

    print("version_check: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
