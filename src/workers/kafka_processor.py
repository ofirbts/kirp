"""
Kafka Event Processor — Real-time event processing pipeline with idempotency, retries, and monitoring.

Consumes from kirp-events topic → Event → RAG → Agent → Governance → Execution → Event.
Writes: events → Mongo, nodes/edges → Postgres, vectors → Qdrant, history → Mongo.
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
from src.models.event import CanonicalEvent
from src.core.event_registry import get_event_registry
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
CONNECT_RETRY_SEC = 5.0  # wait between connection retries at startup

# Metrics
_metrics = MetricsCollector("kirp_kafka")


def _ensure_topic_exists(topic: str) -> None:
    """Create Kafka topic if it does not exist (so consumer can subscribe before any producer runs)."""
    bootstrap = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
    try:
        from confluent_kafka.admin import AdminClient
        admin = AdminClient({"bootstrap.servers": bootstrap})
        try:
            md = admin.list_topics(timeout=10.0)
            if topic in md.topics:
                logger.info("Kafka topic '%s' already exists", topic)
                return
        except Exception as e:
            logger.warning("List topics failed (broker may still be starting): %s", e)
            return
        from confluent_kafka.admin import NewTopic
        fs = admin.create_topics([NewTopic(topic, num_partitions=3, replication_factor=1)])
        for t, f in fs.items():
            try:
                f.result(timeout=10.0)
                logger.info("Created Kafka topic '%s'", t)
            except Exception as e:
                if "already exists" in str(e).lower() or "topic_already_exists" in str(e).lower():
                    logger.info("Kafka topic '%s' already exists", t)
                else:
                    logger.warning("Create topic %s: %s", t, e)
    except ImportError:
        logger.warning("confluent_kafka.admin not available; topic may need to exist already")
    except Exception as e:
        logger.warning("Could not ensure topic %s: %s", topic, e)


def wait_for_topic(consumer: Any, topic: str, delay_seconds: float = 2.0) -> None:
    """
    Wait until Kafka reports that the given topic exists and is usable.
    Prevents UNKNOWN_TOPIC_OR_PART on startup when broker is still warming up.
    Retries indefinitely until the topic is available; never exits or raises.
    """
    attempt = 0
    while True:
        attempt += 1
        try:
            md = consumer.list_topics(timeout=5.0)
            if topic in md.topics:
                logger.info("Kafka topic '%s' is available (attempt %d)", topic, attempt)
                return
            logger.warning("Kafka topic '%s' not found yet (attempt %d)", topic, attempt)
        except Exception as e:
            logger.warning("Kafka not ready yet (attempt %d): %s", attempt, e)
        time.sleep(delay_seconds)


def _get_event_idempotency_key(payload: dict[str, Any]) -> str:
    """Generate idempotency key from event payload."""
    explicit_key = payload.get("idempotency_key") or payload.get("data", {}).get("idempotency_key")
    if explicit_key:
        return f"idem:{explicit_key}"
    event_id = payload.get("data", {}).get("id")
    run_id = payload.get("run_id") or payload.get("data", {}).get("run_id")
    trace_id = payload.get("trace_id") or payload.get("data", {}).get("trace_id")
    if event_id:
        return f"event:{event_id}"
    if run_id:
        return f"run:{run_id}"
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


async def _connect_with_retry(
    name: str,
    connect_fn,
    max_attempts: int = 5,
    delay: float = 1.0,
) -> Any:
    """Call connect_fn() with retries on connection errors; raise after max_attempts."""
    last_err = None
    for attempt in range(1, max_attempts + 1):
        try:
            result = connect_fn()
            if asyncio.iscoroutine(result):
                result = await result
            logger.debug("%s connected (attempt %d)", name, attempt)
            return result
        except Exception as e:
            last_err = e
            logger.warning("%s connection attempt %d/%d failed: %s", name, attempt, max_attempts, e)
            if attempt < max_attempts:
                await asyncio.sleep(delay * attempt)
    raise last_err


async def process_event(payload: dict[str, Any], retry_count: int = 0) -> bool:
    """
    Process single event from Kafka with idempotency and retries.
    Returns True if successful, False otherwise.
    """
    start_time = time.time()
    event_type = payload.get("type", "unknown")
    data = payload.get("data", {})
    run_id_payload = payload.get("run_id") or data.get("run_id")
    workflow_type_payload = payload.get("workflow_type") or data.get("workflow_type") or event_type
    trace_id_payload = payload.get("trace_id") or data.get("trace_id")
    logger.info("KafkaEventAgent received: %s", event_type)
    run_controller = None
    if run_id_payload:
        run_id_str = str(run_id_payload)
        try:
            from src.core.run_controller import get_run_controller
            run_controller = get_run_controller()
            kick_tenant = str(payload.get("tenant_id") or data.get("tenant_id") or "default")
            run_controller.update_key_prefix(kick_tenant)
            await run_controller.create_run(
                workflow_type=str(workflow_type_payload),
                tenant_id=kick_tenant,
                idempotency_key=payload.get("idempotency_key") or data.get("idempotency_key"),
                trace_id=trace_id_payload,
                run_id=run_id_str,
            )
            await run_controller.update_step(run_id_str, "kafka_received", "processing")
        except Exception as e:
            logger.error(
                "run_creation_failed run_id=%s event_type=%s trace_id=%s error=%s",
                run_id_str,
                event_type,
                trace_id_payload,
                e,
                exc_info=True,
            )
            _metrics.inc(
                "events_failed",
                labels={"event_type": event_type, "reason": "run_creation_failed"},
            )
            latency = time.time() - start_time
            _metrics.observe("event_processing_latency", latency, labels={"event_type": event_type, "status": "error"})
            return False

    try:
        # Handle agent_run events: execute agent via engine + framework
        if event_type == "agent_run":
            run_id_s = data.get("run_id")
            agent_name = data.get("agent_name")
            tenant_id = data.get("tenant_id", "default")
            if run_controller:
                run_controller.update_key_prefix(str(tenant_id))
            space_id = data.get("space_id", "all")
            user_id = data.get("user_id", "system")
            context = data.get("input", {})
            if not run_id_s or not agent_name:
                logger.error("agent_run missing run_id or agent_name")
                _metrics.inc("events_failed", labels={"event_type": "agent_run", "reason": "missing_fields"})
                return False
            idempotency_key = f"agent_run:{run_id_s}"
            if await _check_idempotency(idempotency_key):
                logger.info("Agent run already processed (idempotency): %s", run_id_s)
                if run_controller and run_id_payload:
                    await run_controller.update_step(str(run_id_payload), "idempotency_check", "completed")
                return True
            from src.core.agent_engine import get_agent_engine
            run_id = UUID(run_id_s)
            af = get_agent_framework_with_all_agents()
            spec = af.get(agent_name)
            if not spec or not getattr(spec, "handler", None):
                logger.error("Agent not found or no handler: %s", agent_name)
                _metrics.inc("events_failed", labels={"event_type": "agent_run", "reason": "agent_not_found"})
                return False
            engine = get_agent_engine()
            await engine.execute_run(run_id, agent_name, tenant_id, space_id, user_id, context, spec.handler)
            await _mark_processed(idempotency_key)
            if run_controller and run_id_payload:
                await run_controller.update_step(str(run_id_payload), "agent_execute", "completed")
            latency = time.time() - start_time
            _metrics.inc("events_processed", labels={"event_type": "agent_run", "tenant_id": tenant_id})
            logger.info("KafkaProcessor processed agent_run run_id=%s agent=%s latency=%.2fs", run_id_s, agent_name, latency)
            return True

        # Ingest flow: idempotency then pipeline
        idempotency_key = _get_event_idempotency_key(payload)
        if await _check_idempotency(idempotency_key):
            logger.info("Event already processed (idempotency): %s", idempotency_key)
            _metrics.inc("events_duplicate", labels={"event_type": event_type})
            if run_controller and run_id_payload:
                await run_controller.update_step(str(run_id_payload), "idempotency_check", "completed")
            return True
        
        raw_data = payload.get("data") or {}
        # Use envelope/payload values exactly — no fallbacks (multi-tenant: real tenant_id/user_id from JWT)
        tenant_id = payload.get("tenant_id") if payload.get("tenant_id") is not None else raw_data.get("tenant_id")
        space_id = payload.get("space_id") if payload.get("space_id") is not None else raw_data.get("space_id")
        user_id = payload.get("user_id") if payload.get("user_id") is not None else raw_data.get("user_id")
        data = {
            **raw_data,
            "tenant_id": tenant_id,
            "space_id": space_id,
            "user_id": user_id,
            "run_id": payload.get("run_id") or raw_data.get("run_id"),
            "workflow_type": payload.get("workflow_type") or raw_data.get("workflow_type"),
            "trace_id": payload.get("trace_id") or raw_data.get("trace_id"),
            "idempotency_key": payload.get("idempotency_key") or raw_data.get("idempotency_key"),
            "parent_run_id": payload.get("parent_run_id") or raw_data.get("parent_run_id"),
        }
        if not tenant_id or tenant_id == "*":
            logger.error("Invalid tenant_id in Kafka event: %s", tenant_id)
            _metrics.inc("events_failed", labels={"event_type": event_type, "reason": "invalid_tenant"})
            return False
        if not user_id:
            logger.error("Missing user_id in Kafka event (required for multi-tenancy)")
            _metrics.inc("events_failed", labels={"event_type": event_type, "reason": "missing_user_id"})
            return False

        from src.core.run_controller import get_run_controller as _get_rc

        _get_rc().update_key_prefix(str(tenant_id))

        # Initialize components with connection retries (Mongo, Qdrant, Postgres)
        store = EventStore(os.getenv("MONGO_URI", "mongodb://root:example@mongodb:27017/kirp?authSource=admin"))
        await _connect_with_retry("EventStore", lambda: store.connect())

        # Notion / external_id update: if event already exists by external_id, update and run post_ingest only
        meta = data.get("metadata") or {}
        external_id = meta.get("external_id") if isinstance(meta.get("external_id"), str) else None
        source = data.get("source", "")
        if external_id and source:
            existing = await store.find_by_external_id(tenant_id=tenant_id, source=source, external_id=external_id)
            if existing:
                content_str = data.get("text") or data.get("content") or ""
                await store.update_by_external_id(
                    tenant_id, source, external_id,
                    content=content_str,
                    metadata=meta,
                )
                rag = RAGEngine(
                    qdrant_url=os.getenv("QDRANT_URL", "http://qdrant:6333"),
                    qdrant_api_key=os.getenv("QDRANT_API_KEY"),
                    embedding_provider=os.getenv("EMBEDDING_PROVIDER", "openai"),
                    embedding_model=os.getenv("EMBEDDING_MODEL", "text-embedding-3-small"),
                )
                await _connect_with_retry("RAGEngine", lambda: rag.connect())
                from src.core.schema_engine import SchemaEngine
                schema = SchemaEngine(os.getenv("POSTGRES_URI", "postgresql+asyncpg://kirp_user:kirp_password@postgres:5432/kirp"))
                await _connect_with_retry("SchemaEngine", lambda: schema.connect())
                gov = GovernanceEngine(os.getenv("OPA_URL", "http://opa:8181"))
                af = get_agent_framework_with_all_agents()
                pipe = EventPipeline(store, rag, schema, gov, af)
                await pipe.run_post_ingest_for_event(existing.id)
                await _mark_processed(idempotency_key)
                _metrics.inc("events_processed", labels={"event_type": event_type, "tenant_id": tenant_id})
                logger.info("KafkaProcessor processed ingest (update by external_id) source=%s ext=%s", source, external_id)
                return True

        # Idempotency: if event was already stored (e.g. legacy API sent event_id), skip
        event_id_raw = data.get("id")
        if event_id_raw:
            try:
                ev_uuid = UUID(event_id_raw)
                existing = await store.get_by_id(ev_uuid)
                if existing:
                    await _mark_processed(idempotency_key)
                    logger.info("Event already in store (idempotency), skipping pipeline: %s", event_id_raw)
                    _metrics.inc("events_duplicate", labels={"event_type": event_type})
                    return True
            except (ValueError, TypeError):
                pass

        # Build CanonicalEvent and dispatch via EventRegistry (ingest → pipeline → history/tasks/graph)
        data_for_canonical = {
            **data,
            "event_type": event_type,
            "content": data.get("text") or data.get("content") or "",
        }
        canonical = CanonicalEvent.from_payload(data_for_canonical)
        logger.info(
            "[INGEST] event created: id=%s run=%s wf=%s tenant=%s space=%s user=%s source=%s len=%d",
            canonical.id, canonical.run_id, canonical.workflow_type,
            canonical.tenant_id, canonical.space_id, canonical.user_id,
            canonical.source, len(canonical.content),
        )
        # Close kafka_received before dispatch so aggregate state is not stuck on "processing" forever.
        if run_controller and run_id_payload:
            await run_controller.update_step(str(run_id_payload), "kafka_received", "completed")
        registry = get_event_registry()
        if run_controller and run_id_payload:
            await run_controller.update_step(str(run_id_payload), "registry_dispatch", "processing")
        await registry.dispatch(canonical)
        if run_controller and run_id_payload:
            await run_controller.update_step(str(run_id_payload), "registry_dispatch", "completed")
        logger.info(
            "[INGEST] event processed: id=%s run=%s tenant=%s user=%s (history/tasks/graph written)",
            canonical.id, canonical.run_id, canonical.tenant_id, canonical.user_id,
        )

        # Mark as processed
        await _mark_processed(idempotency_key)
        if run_controller and run_id_payload:
            await run_controller.update_step(str(run_id_payload), "kafka_processed", "completed")
        
        # Metrics
        latency = time.time() - start_time
        _metrics.observe("event_processing_latency", latency, labels={"event_type": event_type})
        _metrics.inc("events_processed", labels={"event_type": event_type, "tenant_id": tenant_id})
        
        logger.info("KafkaProcessor processed: %s run=%s trace=%s tenant=%s latency=%.2fs",
                    event_type, canonical.run_id, canonical.trace_id, tenant_id, latency)
        return True
        
    except Exception as e:
        if run_controller and run_id_payload:
            try:
                await run_controller.update_step(str(run_id_payload), "kafka_failed", "failed", error=str(e))
            except Exception:
                pass
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
    """Consume events from Kafka forever with monitoring and error recovery. Retries connections instead of exiting."""
    consumer = None
    attempt = 0
    while consumer is None:
        attempt += 1
        logger.info("Connecting to Kafka (attempt %s)...", attempt)
        consumer = get_kafka_consumer("kirp-processor", [EVENT_TOPIC], subscribe=False)
        if consumer is None:
            logger.warning("Kafka consumer not available yet; retrying in %.0fs", CONNECT_RETRY_SEC)
            await asyncio.sleep(CONNECT_RETRY_SEC)
    logger.info("Kafka consumer created; ensuring topic '%s' exists", EVENT_TOPIC)
    _ensure_topic_exists(EVENT_TOPIC)
    wait_for_topic(consumer, EVENT_TOPIC)
    consumer.subscribe([EVENT_TOPIC])

    logger.info("KafkaProcessor started (topic=%s); consuming messages", EVENT_TOPIC)
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
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    logger.info("Starting kirp-agent-processor (topic=%s)", EVENT_TOPIC)
    asyncio.run(consume_forever())
