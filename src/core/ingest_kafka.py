"""
Ingest → Kafka — Publish unified ingest events to kirp-events for downstream agents.

Called after pipeline.run() so all events flow: API/connectors → pipeline → EventStore → Kafka.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from src.core.event_store import Event

logger = logging.getLogger(__name__)

EVENT_TOPIC = "kirp-events"


async def publish_ingest_event(event: Event) -> None:
    """Publish event to Kafka (best-effort). Non-blocking."""
    try:
        from src.core.integrations import get_kafka_producer
        producer = get_kafka_producer()
        if not producer:
            return
        payload: dict[str, Any] = {"type": "ingest", "data": event.to_json_payload()}
        value = json.dumps(payload, default=str)

        def _produce() -> None:
            producer.produce(EVENT_TOPIC, value=value.encode("utf-8"))
            producer.flush(timeout=2)

        await asyncio.to_thread(_produce)
        logger.debug("Published ingest event to Kafka: %s", event.trace_id)
    except Exception as e:
        logger.warning("Kafka publish failed: %s", e)
        raise
