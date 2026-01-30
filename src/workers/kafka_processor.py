"""
Kafka Event Processor — Real-time event processing pipeline with idempotency, retries, and monitoring.

Consumes from kirp-events topic → Event → RAG → Agent → Governance → Execution → Event
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import time
from typing import Any

from src.core.integrations import get_kafka_consumer, get_redis_async
from src.core.event_store import EventStore, Event, Sensitivity
from src.core.rag_engine import RAGEngine
from src.core.agent_registry import get_agent_framework_with_all_agents
from src.core.governance import GovernanceEngine
from src.core.pipeline import EventPipeline
from src.observability.metrics import MetricsCollector
from uuid import UUID, uuid4
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

EVENT_TOPIC = "kirp-events"
MAX_RETRIES = 3
RETRY_DELAY = 1.0  # seconds
IDEMPOTENCY_TTL = 3600  # 1 hour

# Metrics
_metrics = MetricsCollector("kirp_kafka")


def _get_event_idempotency_key(payload: dict[str, Any]) -> str:
    """Generate idempotency key from event payload."""
    event_id = payload.get("data", {}).get("id")
    trace_id = payload.get("trace_id")
    if event_id:
        return f"event:{event_id}"
    if trace_id:
        return f"trace:{trace_id}"
    # Fallback: hash payload
    payload_str = json.dumps(payload, sort_keys=True)
    return f"hash:{hashlib.sha256(payload_str.encode()).hexdigest()}"


async def _check_idempotency(key: str) -> bool:
    """Check if event was already processed (idempotency)."""
    try:
        redis = await get_redis_async()
        if redis:
            exists = await redis.exists(f"idempotency:{key}")
            return exists > 0
    except Exception as e:
        logger.warning("Idempotency check failed: %s", e)
    return False


async def _mark_processed(key: str) -> None:
    """Mark event as processed (idempotency)."""
    try:
        redis = await get_redis_async()
        if redis:
            await redis.setex(f"idempotency:{key}", IDEMPOTENCY_TTL, "1")
    except Exception as e:
        logger.warning("Failed to mark event as processed: %s", e)


async def process_event(payload: dict[str, Any], retry_count: int = 0) -> bool:
    """
    Process single event from Kafka with idempotency and retries.
    Returns True if successful, False otherwise.
    """
    start_time = time.time()
    event_type = payload.get("type", "unknown")
    
    try:
        # Idempotency check
        idempotency_key = _get_event_idempotency_key(payload)
        if await _check_idempotency(idempotency_key):
            logger.info("Event already processed (idempotency): %s", idempotency_key)
            _metrics.inc("events_duplicate", labels={"event_type": event_type})
            return True
        
        data = payload.get("data", {})
        
        # Enforce multi-tenant isolation
        tenant_id = data.get("tenant_id", "system")
        if not tenant_id or tenant_id == "*":
            logger.error("Invalid tenant_id in Kafka event: %s", tenant_id)
            _metrics.inc("events_failed", labels={"event_type": event_type, "reason": "invalid_tenant"})
            return False

        # Initialize components (with connection pooling in production)
        store = EventStore(os.getenv("MONGO_URI", "mongodb://root:example@mongodb:27017/kirp?authSource=admin"))
        await store.connect()
        rag = RAGEngine(qdrant_url=os.getenv("QDRANT_URL", "http://qdrant:6333"))
        await rag.connect()
        from src.core.schema_engine import SchemaEngine
        schema = SchemaEngine(os.getenv("POSTGRES_URI", "postgresql+asyncpg://kirp_user:kirp_password@postgres:5432/kirp"))
        await schema.connect()
        gov = GovernanceEngine(os.getenv("OPA_URL", "http://opa:8181"))
        af = get_agent_framework_with_all_agents()

        # Create event
        ev = Event(
            id=UUID(data.get("id", str(uuid4()))),
            tenant_id=tenant_id,
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

        # Run pipeline (preserve event id from Kafka payload)
        pipe = EventPipeline(store, rag, schema, gov, af)
        await pipe.run(
            tenant_id=ev.tenant_id,
            space_id=ev.space_id,
            user_id=ev.user_id,
            source=ev.source,
            content=ev.content,
            metadata=ev.metadata,
            sensitivity=ev.sensitivity,
            event_id=ev.id,
        )

        # Mark as processed
        await _mark_processed(idempotency_key)
        
        # Metrics
        latency = time.time() - start_time
        _metrics.observe("event_processing_latency", latency, labels={"event_type": event_type})
        _metrics.inc("events_processed", labels={"event_type": event_type, "tenant_id": tenant_id})
        
        logger.info("KafkaProcessor processed: %s trace=%s tenant=%s latency=%.2fs", 
                   event_type, ev.trace_id, tenant_id, latency)
        return True
        
    except Exception as e:
        latency = time.time() - start_time
        _metrics.inc("events_failed", labels={"event_type": event_type, "retry": str(retry_count)})
        _metrics.observe("event_processing_latency", latency, labels={"event_type": event_type, "status": "error"})
        
        logger.exception("KafkaProcessor failed (retry %d/%d): %s", retry_count, MAX_RETRIES, e)
        
        # Retry logic
        if retry_count < MAX_RETRIES:
            await asyncio.sleep(RETRY_DELAY * (retry_count + 1))  # Exponential backoff
            return await process_event(payload, retry_count + 1)
        else:
            logger.error("KafkaProcessor max retries exceeded for event: %s", payload.get("trace_id"))
            return False


async def consume_forever() -> None:
    """Consume events from Kafka forever with monitoring and error recovery."""
    consumer = get_kafka_consumer("kirp-processor", [EVENT_TOPIC])
    if consumer is None:
        logger.error("Kafka consumer not available")
        return

    logger.info("KafkaProcessor started (topic=%s)", EVENT_TOPIC)
    _metrics.gauge("kafka_consumer_status", 1.0, labels={"status": "running"})
    
    consecutive_errors = 0
    max_consecutive_errors = 10
    
    while True:
        try:
            msg = consumer.poll(timeout=1.0)
            if msg is None:
                await asyncio.sleep(0.1)
                consecutive_errors = 0  # Reset on successful poll
                continue
            
            if msg.error():
                logger.error("Kafka error: %s", msg.error())
                _metrics.inc("kafka_errors", labels={"type": "consumer_error"})
                consecutive_errors += 1
                if consecutive_errors >= max_consecutive_errors:
                    logger.error("Too many consecutive errors, backing off")
                    await asyncio.sleep(5)
                    consecutive_errors = 0
                continue
            
            try:
                payload = json.loads(msg.value().decode("utf-8"))
                success = await process_event(payload)
                
                if success:
                    # Commit offset on success
                    consumer.commit(msg)
                    consecutive_errors = 0
                else:
                    # Don't commit on failure - will retry
                    logger.warning("Event processing failed, not committing offset")
                    consecutive_errors += 1
                    
            except json.JSONDecodeError as e:
                logger.error("Failed to parse Kafka message: %s", e)
                _metrics.inc("kafka_errors", labels={"type": "parse_error"})
                # Commit even on parse error to avoid infinite loop
                consumer.commit(msg)
                
        except KeyboardInterrupt:
            logger.info("KafkaProcessor stopping")
            _metrics.gauge("kafka_consumer_status", 0.0, labels={"status": "stopped"})
            consumer.close()
            break
        except Exception as e:
            logger.exception("KafkaProcessor loop error: %s", e)
            _metrics.inc("kafka_errors", labels={"type": "loop_error"})
            consecutive_errors += 1
            if consecutive_errors >= max_consecutive_errors:
                logger.error("Too many consecutive errors, backing off")
                await asyncio.sleep(5)
                consecutive_errors = 0
            else:
                await asyncio.sleep(1)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(consume_forever())
