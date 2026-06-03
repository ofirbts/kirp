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
        any(k in p.lower() for k in ("auth", "docker", "compose", "migration", "schema"))
        for p in changed
    )
    if critical:
        print(
            json.dumps(
                {
                    "permission": "deny",
                    "user_message": "Commit blocked: critical files are staged. Run required checks (lint/build/tests + deploy checks if relevant) before committing.",
                    "agent_message": "Pre-commit guard: commit blocked for critical scope.",
                }
            )
        )
        return 1

    print(json.dumps({"permission": "allow"}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
