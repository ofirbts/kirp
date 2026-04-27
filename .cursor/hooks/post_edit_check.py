#!/usr/bin/env python3
import json
import sys


CRITICAL_MARKERS = (
    "auth",
    "api",
    "migration",
    "docker",
    "compose",
    "deploy",
    "schema",
)


def main() -> int:
    raw = sys.stdin.read().strip()
    payload = json.loads(raw) if raw else {}
    path = str(payload.get("file_path", "")).lower()
    if any(marker in path for marker in CRITICAL_MARKERS):
        print(
            json.dumps(
                {
                    "additional_context": "Critical area touched. Confirm approval scope and run /test plus /deploy-check before merge."
                }
            )
        )
        return 0
    print(json.dumps({}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
