#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

ALLOWED_GET_BY_ID_FILES = {
    SRC / "core" / "event_store.py",
}

def main() -> int:
    errors: list[str] = []
    for path in SRC.rglob("*.py"):
        if path in ALLOWED_GET_BY_ID_FILES:
            continue
        text = path.read_text(encoding="utf-8")
        if ".get_by_id(" in text:
            rel = path.relative_to(ROOT)
            errors.append(f"{rel}: unscoped get_by_id — use get_by_id_for_tenant")
    count_events_def = (SRC / "core" / "event_store.py").read_text(encoding="utf-8")
    if "tenant_id: str | None" in count_events_def and "count_events" in count_events_def:
        errors.append("event_store.py: count_events must require tenant_id")
    if errors:
        print("tenant_isolation_gate: FAIL")
        for e in errors:
            print(f"  - {e}")
        return 1
    print("tenant_isolation_gate: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
