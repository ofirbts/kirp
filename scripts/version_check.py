#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import re
import sys


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    main_py = root / "src" / "main.py"
    health_test = root / "tests" / "test_health_versioning.py"

    if not main_py.exists():
        print("version_check: missing src/main.py")
        return 2
    if not health_test.exists():
        print("version_check: missing tests/test_health_versioning.py")
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
        return 4

    print("version_check: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
