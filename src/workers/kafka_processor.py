"""
Kafka Event Processor — Real-time event processing pipeline.

Consumes from kirp-events topic → Event → RAG → Agent → Governance → Execution → Event
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Any

from src.core.integrations import get_kafka_consumer
from src.core.event_store import EventStore, Event, Sensitivity
from src.core.rag_engine import RAGEngine
from src.core.agent_framework import AgentFramework
from src.core.governance import GovernanceEngine
from src.core.pipeline import EventPipeline
from src.agents import (
    pattern_analyzer_spec,
    planner_spec,
    forecaster_spec,
    risk_opportunity_spec,
    schema_structure_spec,
    presentation_spec,
    self_improvement_spec,
)
from uuid import UUID, uuid4
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

EVENT_TOPIC = "kirp-events"


async def process_event(payload: dict[str, Any]) -> None:
    """Process single event from Kafka."""
    try:
        event_type = payload.get("type", "unknown")
        data = payload.get("data", {})

        # Initialize components
        store = EventStore(os.getenv("MONGO_URI", "mongodb://root:example@mongodb:27017/kirp?authSource=admin"))
        await store.connect()
        rag = RAGEngine(qdrant_url=os.getenv("QDRANT_URL", "http://qdrant:6333"))
        await rag.connect()
        from src.core.schema_engine import SchemaEngine
        schema = SchemaEngine(os.getenv("POSTGRES_URI", "postgresql+asyncpg://kirp_user:kirp_password@postgres:5432/kirp"))
        await schema.connect()
        gov = GovernanceEngine(os.getenv("OPA_URL", "http://opa:8181"))
        af = AgentFramework()
        for spec in (
            pattern_analyzer_spec,
            planner_spec,
            forecaster_spec,
            risk_opportunity_spec,
            schema_structure_spec,
            presentation_spec,
            self_improvement_spec,
        ):
            af.register(spec)

        # Create event
        ev = Event(
            id=UUID(data.get("id", str(uuid4()))),
            tenant_id=data.get("tenant_id", "system"),
            space_id=data.get("space_id", "system"),
            user_id=data.get("user_id", "system"),
            source=data.get("source", "kafka"),
            content=data.get("content", ""),
            metadata=data.get("metadata", {}),
            embedding=[],
            timestamp=datetime.now(timezone.utc),
            sensitivity=Sensitivity(data.get("sensitivity", "private")),
            event_type=event_type,
            trace_id=data.get("trace_id"),
        )

        # Run pipeline
        pipe = EventPipeline(store, rag, schema, gov, af)
        await pipe.run(
            tenant_id=ev.tenant_id,
            space_id=ev.space_id,
            user_id=ev.user_id,
            source=ev.source,
            content=ev.content,
            metadata=ev.metadata,
            sensitivity=ev.sensitivity,
        )

        logger.info("KafkaProcessor processed: %s trace=%s", event_type, ev.trace_id)
    except Exception as e:
        logger.exception("KafkaProcessor failed: %s", e)


async def consume_forever() -> None:
    """Consume events from Kafka forever."""
    consumer = get_kafka_consumer("kirp-processor", [EVENT_TOPIC])
    if consumer is None:
        logger.error("Kafka consumer not available")
        return

    logger.info("KafkaProcessor started (topic=%s)", EVENT_TOPIC)
    while True:
        try:
            msg = consumer.poll(timeout=1.0)
            if msg is None:
                await asyncio.sleep(0.1)
                continue
            if msg.error():
                logger.error("Kafka error: %s", msg.error())
                continue
            payload = json.loads(msg.value().decode("utf-8"))
            await process_event(payload)
        except KeyboardInterrupt:
            logger.info("KafkaProcessor stopping")
            consumer.close()
            break
        except Exception as e:
            logger.exception("KafkaProcessor loop error: %s", e)
            await asyncio.sleep(1)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(consume_forever())
