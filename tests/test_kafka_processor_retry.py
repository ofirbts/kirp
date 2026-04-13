"""Controlled failure: processor retries once when registry.dispatch raises, same trace_id in retry log."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from src.workers.kafka_processor import process_event


def _ingest_payload() -> dict:
    return {
        "type": "ingest",
        "tenant_id": "tenant_retry_test",
        "space_id": "space1",
        "user_id": "user1",
        "run_id": "run_retry_verify",
        "trace_id": "tr_retry_verify",
        "workflow_type": "ingest_event",
        "idempotency_key": "idem-retry-test",
        "data": {
            "text": "hello",
            "tenant_id": "tenant_retry_test",
            "space_id": "space1",
            "user_id": "user1",
            "source": "retry_test",
            "run_id": "run_retry_verify",
            "trace_id": "tr_retry_verify",
        },
    }


def test_process_event_retries_once_when_dispatch_raises_once() -> None:
    captured: list[tuple[str, dict]] = []

    def capture_log(_logger, _level: str, event: str, **fields) -> None:
        captured.append((event, dict(fields)))

    dispatch_calls: list[int] = []

    async def dispatch_side_effect(_canonical) -> None:
        dispatch_calls.append(1)
        if len(dispatch_calls) == 1:
            raise RuntimeError("simulated_dispatch_failure")

    async def _run() -> bool:
        rc = MagicMock()
        rc.update_key_prefix = MagicMock()
        rc.create_run = AsyncMock()
        rc.update_step = AsyncMock()

        registry = MagicMock()
        registry.dispatch = AsyncMock(side_effect=dispatch_side_effect)

        mock_store_inst = MagicMock()
        mock_store_inst.connect = MagicMock()

        mock_metrics = MagicMock()

        with (
            patch("src.workers.kafka_processor.log_json", side_effect=capture_log),
            patch("src.workers.kafka_processor._check_idempotency", new_callable=AsyncMock, return_value=False),
            patch("src.workers.kafka_processor._mark_processed", new_callable=AsyncMock),
            patch("src.workers.kafka_processor.EventStore", return_value=mock_store_inst),
            patch("src.workers.kafka_processor._connect_with_retry", new_callable=AsyncMock),
            patch("src.workers.kafka_processor._metrics", mock_metrics),
            patch("src.core.run_controller.get_run_controller", return_value=rc),
            patch("src.workers.kafka_processor.get_event_registry", return_value=registry),
            patch("asyncio.sleep", new_callable=AsyncMock),
        ):
            return await process_event(_ingest_payload())

    ok = asyncio.run(_run())

    assert ok is True
    assert len(dispatch_calls) == 2
    retry_logs = [f for ev, f in captured if ev == "kafka_processor_retrying"]
    assert len(retry_logs) == 1
    assert retry_logs[0]["trace_id"] == "tr_retry_verify"
    assert retry_logs[0]["run_id"] == "run_retry_verify"
    assert retry_logs[0]["tenant_id"] == "tenant_retry_test"
    fail_logs = [f for ev, f in captured if ev == "kafka_processor_failed" and f.get("step") == "kafka_process"]
    assert len(fail_logs) == 1
    assert fail_logs[0]["retry_count"] == 0
