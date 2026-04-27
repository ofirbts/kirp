#!/usr/bin/env python3
import json
import subprocess
import sys


def main() -> int:
    try:
        changed = subprocess.check_output(
            ["git", "diff", "--name-only", "--cached"],
            text=True,
        ).splitlines()
    except Exception:
        changed = []

    critical = any(
        any(k in p.lower() for k in ("auth", "docker", "compose", "migration", "schema", "api"))
        for p in changed
    )
    if critical:
        print(
            json.dumps(
                {
                    "permission": "ask",
                    "user_message": "Critical files staged. Confirm required checks (lint/build/tests + deploy checks if relevant).",
                    "agent_message": "Pre-commit guard: critical scope detected.",
                }
            )
        )
        return 0

    print(json.dumps({"permission": "allow"}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
