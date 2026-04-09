"""
Kafka Event Agent — Producer/Consumer for event bus.

Emits events to Kafka; consumes and triggers agents.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any

from src.core.integrations import get_kafka_producer, get_kafka_consumer

logger = logging.getLogger(__name__)

EVENT_TOPIC = "kirp-events"


@dataclass
class EventEnvelope:
    """Event envelope for Kafka. tenant_id, space_id, user_id must be provided (no defaults)."""

    type: str
    payload: dict[str, Any]
    tenant_id: str
    space_id: str
    user_id: str
    run_id: str | None = None
    workflow_type: str | None = None
    trace_id: str | None = None
    idempotency_key: str | None = None
    parent_run_id: str | None = None


class KafkaEventAgent:
    """Kafka event producer/consumer."""

    def emit(self, event: EventEnvelope) -> bool:
        """Emit event to Kafka topic."""
        producer = get_kafka_producer()
        if producer is None:
            logger.warning("Kafka producer not available")
            return False
        try:
            envelope = {
                "type": event.type,
                "data": event.payload,
                "tenant_id": event.tenant_id,
                "space_id": event.space_id,
                "user_id": event.user_id,
                "run_id": event.run_id,
                "workflow_type": event.workflow_type,
                "trace_id": event.trace_id,
                "idempotency_key": event.idempotency_key,
                "parent_run_id": event.parent_run_id,
            }
            producer.produce(
                EVENT_TOPIC,
                key=event.type.encode("utf-8"),
                value=json.dumps(envelope, default=str).encode("utf-8"),
            )
            producer.flush(timeout=5.0)
            logger.info("KafkaEventAgent emitted: %s", event.type)
            return True
        except Exception as e:
            logger.error("Kafka emit failed: %s", e)
            return False

    def consume_forever(self, group_id: str = "kirp-event-consumer", handler: Any = None) -> None:
        """Consume events from Kafka forever."""
        consumer = get_kafka_consumer(group_id, [EVENT_TOPIC])
        if consumer is None:
            logger.warning("Kafka consumer not available")
            return
        logger.info("KafkaEventAgent consuming from %s (group=%s)", EVENT_TOPIC, group_id)
        while True:
            try:
                msg = consumer.poll(timeout=1.0)
                if msg is None:
                    continue
                if msg.error():
                    logger.error("Kafka consumer error: %s", msg.error())
                    continue
                payload = json.loads(msg.value().decode("utf-8"))
                logger.info("KafkaEventAgent received: %s", payload.get("type", "unknown"))
                if handler:
                    handler(payload)
            except KeyboardInterrupt:
                logger.info("KafkaEventAgent stopping")
                consumer.close()
                break
            except Exception as e:
                logger.exception("Kafka consume error: %s", e)
