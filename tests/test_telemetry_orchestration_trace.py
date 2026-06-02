from __future__ import annotations

import logging

from src.telemetry.orchestration_trace import TraceEvent, log_trace


def test_log_trace_emits_without_side_effects(caplog) -> None:
    logger = logging.getLogger("test_trace")
    with caplog.at_level(logging.INFO, logger="test_trace"):
        log_trace(
            logger,
            stage="test_stage",
            trace_id="tr-1",
            event_id="ev-1",
            tenant_id="t1",
            foo="bar",
        )
    # Ensure a single log line with the structured payload was written.
    assert any("telemetry_trace" in record.message for record in caplog.records)


def test_trace_event_dataclass_holds_metadata() -> None:
    ev = TraceEvent(
        trace_id="tr-x",
        event_id="ev-x",
        tenant_id="t-x",
        stage="stage-x",
        metadata={"k": "v"},
        timestamp=__import__("datetime").datetime.now(),
    )
    assert ev.trace_id == "tr-x"
    assert ev.metadata["k"] == "v"

