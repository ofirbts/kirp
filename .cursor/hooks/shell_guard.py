#!/usr/bin/env python3
import json
import re
import sys


def main() -> int:
    raw = sys.stdin.read().strip()
    payload = json.loads(raw) if raw else {}
    cmd = str(payload.get("command", "")).strip()
    blocked = [
        r"\bgit\s+reset\s+--hard\b",
        r"\bgit\s+checkout\s+--\b",
        r"\brm\s+-rf\b",
    ]
    for pattern in blocked:
        if re.search(pattern, cmd):
            print(
                json.dumps(
                    {
                        "permission": "deny",
                        "user_message": "Blocked risky command by OpenClaw safety hook.",
                        "agent_message": "Use a non-destructive alternative or request explicit approval."
                    }
                )
            )
            return 0
    print(json.dumps({"permission": "allow"}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
