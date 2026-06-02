from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from src.core.structured_logging import log_json
from src.telemetry.trace_sink import append_telemetry_line
import logging


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TraceEvent:
    trace_id: Optional[str]
    event_id: Optional[str]
    tenant_id: Optional[str]
    stage: str
    metadata: Dict[str, Any]
    timestamp: datetime


def log_trace(
    logger: logging.Logger,
    stage: str,
    *,
    trace_id: Optional[str] = None,
    event_id: Optional[str] = None,
    tenant_id: Optional[str] = None,
    **metadata: Any,
) -> None:
    ts = datetime.now(timezone.utc).isoformat()
    log_json(
        logger,
        "info",
        "telemetry_trace",
        stage=stage,
        trace_id=trace_id,
        event_id=event_id,
        tenant_id=tenant_id,
        timestamp=ts,
        **metadata,
    )
    payload: Dict[str, Any] = {
        "event": "telemetry_trace",
        "stage": stage,
        "timestamp": ts,
    }
    if trace_id is not None:
        payload["trace_id"] = trace_id
    if event_id is not None:
        payload["event_id"] = event_id
    if tenant_id is not None:
        payload["tenant_id"] = tenant_id
    payload.update(metadata)
    append_telemetry_line(payload)

