from __future__ import annotations

import json
import os
import threading
from typing import Any

_lock = threading.Lock()

_DEV_TRACE_DEFAULT = "/tmp/kirp-traces.jsonl"


def development_env() -> bool:
    env = (os.getenv("ENV") or "").strip().lower()
    return env in {"development", "dev", "local"}


def trace_log_path() -> str:
    explicit = (os.getenv("KIRP_TRACE_LOG_PATH") or "").strip()
    if explicit:
        return explicit
    if development_env():
        return _DEV_TRACE_DEFAULT
    return ""


def append_telemetry_line(payload: dict[str, Any], *, log_path: str | None = None) -> bool:
    path = (log_path or trace_log_path()).strip()
    if not path:
        return False
    line = json.dumps(payload, default=str, ensure_ascii=True)
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with _lock:
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(line + "\n")
    return True


def list_trace_ids_from_file(log_path: str, *, limit: int = 100) -> tuple[str, ...]:
    if not log_path or not os.path.exists(log_path):
        return ()
    counts: dict[str, int] = {}
    with open(log_path, "r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            text = line.strip()
            if not text:
                continue
            start = text.find("{")
            if start < 0:
                continue
            try:
                obj = json.loads(text[start:])
            except Exception:
                continue
            if obj.get("event") != "telemetry_trace":
                continue
            trace_id = obj.get("trace_id")
            if not isinstance(trace_id, str) or not trace_id:
                continue
            counts[trace_id] = counts.get(trace_id, 0) + 1
    ordered = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    return tuple(trace_id for trace_id, _ in ordered[: max(limit, 0)])
