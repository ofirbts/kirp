"""Tiny JSON logging helper for critical-path observability."""

from __future__ import annotations

import json
import logging
from typing import Any

# Include JSON null so grep/aggregators see a stable schema on critical paths.
_NULLABLE_IDENTITY_KEYS = frozenset({"tenant_id", "run_id", "trace_id"})


def log_json(logger: logging.Logger, level: str, event: str, **fields: Any) -> None:
    payload: dict[str, Any] = {"event": event}
    for k, v in fields.items():
        if k in _NULLABLE_IDENTITY_KEYS and v is None:
            payload[k] = None
        elif v is not None:
            payload[k] = v
    line = json.dumps(payload, default=str, ensure_ascii=True)
    fn = getattr(logger, level, logger.info)
    fn(line)
