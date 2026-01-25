# app/core/worker.py
"""
KIRP Enterprise Worker v10
Production-ready Redis worker:
- Multi-queue (high / normal / low)
- Retry with backoff
- Dead-letter queue
- אינטגרציה עם:
  - ingestion pipeline
  - WhatsApp gateway
  - PersistenceManager (jobs + events)
"""

import asyncio
import json
import logging
import os
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Any, Optional

import redis.asyncio as redis

from app.core.persistence import PersistenceManager
from app.services.pipeline import ingest_text
from app.integrations.whatsapp_gateway import wa_gateway
from app.core.metrics import MetricsCollector

logger = logging.getLogger("KIRP-Worker")
metrics = MetricsCollector("worker")


class WorkerStatus(Enum):
    IDLE = "idle"
    PROCESSING = "processing"
    RETRYING = "retrying"
    DEAD_LETTER = "dead_letter"


class EnterpriseWorker:
    """Production distributed worker"""

    def __init__(self, queues: Dict[str, str]):
        self.queues = queues
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.max_retries = int(os.getenv("WORKER_MAX_RETRIES", "5"))
        self.timeout_seconds = int(os.getenv("WORKER_TIMEOUT_SECONDS", "30"))
        self.redis: Optional[redis.Redis] = None
        self.worker_id = f"worker_{uuid.uuid4().hex[:6]}"

    async def connect(self):
        """Production Redis connection"""
        try:
            self.redis = redis.from_url(
                self.redis_url,
                decode_responses=True,
                socket_connect_timeout=5,
                retry_on_timeout=True,
            )
            await self.redis.ping()
            logger.info(f"✅ Enterprise Worker connected to Redis @ {self.redis_url}")
        except Exception as e:
            logger.error(f"❌ Redis connection failed: {e}")
            self.redis = None

    async def _update_job_status(
        self,
        job_id: Optional[str],
        status: str,
        progress: Optional[float] = None,
        error: Optional[str] = None,
    ):
        if not job_id:
            return
        try:
            await PersistenceManager.save_event(
                "job_status_update",
                {
                    "job_id": job_id,
                    "status": status,
                    "progress": progress,
                    "error": error,
                    "worker_id": self.worker_id,
                },
            )
        except Exception as e:
            logger.warning(f"⚠️ Failed to persist job status for {job_id}: {e}")

    async def _handle_ingest(self, payload: Dict[str, Any], job_id: str):
        text = payload.get("text", "")
        user_id = payload.get("user_id", "system")
        source = payload.get("source", "worker_ingest")
        metadata = payload.get("metadata") or {}

        await self._update_job_status(job_id, "processing", progress=0.1)

        result = await ingest_text(
            text=text,
            source=source,
            metadata=metadata,
            user_id=user_id,
        )

        await self._update_job_status(job_id, "completed", progress=1.0)
        await PersistenceManager.append_event(
            "ingest_job_completed",
            {
                "job_id": job_id,
                "user_id": user_id,
                "source": source,
                "result": result,
            },
        )

    async def _handle_whatsapp(self, payload: Dict[str, Any], job_id: str):
        """
        WhatsApp handler:
        payload:
        {
          "to": str,
          "text": str,
          "user_id": str
        }
        """
        to = payload.get("to")
        text = payload.get("text", "")
        user_id = payload.get("user_id", "system")

        await self._update_job_status(job_id, "processing", progress=0.1)

        res = await asyncio.to_thread(wa_gateway.send_message, to, text)

        await self._update_job_status(job_id, "completed", progress=1.0)
        await PersistenceManager.append_event(
            "whatsapp_message_sent",
            {
                "job_id": job_id,
                "user_id": user_id,
                "to": to,
                "preview": text[:160],
                "provider_response": res,
            },
        )

    async def process_event(self, event: Dict[str, Any]) -> bool:
        """
        Main event processing.
        Expected event format:
        {
          "type": "<event_type>",
          "data": {...},
          "id": "<optional>",
          "_retries": int
        }
        """
        event_type = event.get("type", "unknown")
        payload = event.get("data", {}) or {}
        job_id = payload.get("job_id") or event.get("id") or f"job_{uuid.uuid4().hex[:8]}"

        logger.info(f"🔄 Processing {event_type}: {job_id}")
        metrics.inc(f"worker.event.{event_type}")

        try:
            await self._update_job_status(job_id, "processing", progress=0.0)

            if event_type == "ingest_request":
                await self._handle_ingest(payload, job_id)
            elif event_type == "whatsapp_msg":
                await self._handle_whatsapp(payload, job_id)
            else:
                logger.warning(f"⚠️ Unknown event type: {event_type}")
                await self._update_job_status(job_id, "ignored", progress=1.0)
                return True

            logger.info(f"✅ Completed {event_type}: {job_id}")
            metrics.inc("worker.success")
            return True

        except asyncio.TimeoutError:
            logger.error(f"💀 Timeout {job_id}")
            metrics.inc("worker.timeout")
            await self._update_job_status(job_id, "timeout", error="timeout")
            return False
        except Exception as e:
            logger.error(f"❌ Failed {job_id}: {e}")
            metrics.inc("worker.failure")
            await self._update_job_status(job_id, "failed", error=str(e))
            return False

    async def run(self):
        """Main worker loop"""
        logger.info(f"🚀 Starting KIRP Worker [{self.worker_id}]...")
        await self.connect()

        if not self.redis:
            logger.error("❌ Cannot start worker without Redis")
            return

        queues_list = list(self.queues.values())
        logger.info(f"📥 Subscribed queues: {queues_list}")

        while True:
            try:
                result = await self.redis.blpop(queues_list, timeout=5)

                if not result:
                    metrics.inc("worker.idle")
                    await asyncio.sleep(0.1)
                    continue

                queue_name, raw_event = result
                metrics.inc(f"worker.queue.{queue_name}")

                try:
                    event = json.loads(raw_event)
                except Exception:
                    logger.error(f"❌ Invalid event JSON from {queue_name}: {raw_event}")
                    metrics.inc("worker.invalid_event")
                    continue

                retries = int(event.get("_retries", 0))

                success = await self.process_event(event)

                if not success and retries < self.max_retries:
                    # Retry logic with exponential backoff
                    event["_retries"] = retries + 1
                    backoff = min(2 ** retries, 30)
                    logger.warning(
                        f"🔁 Retry {event.get('type')} (job={event.get('id')}) in {backoff}s "
                        f"[attempt {retries + 1}/{self.max_retries}]"
                    )
                    metrics.inc("worker.retry")
                    await asyncio.sleep(backoff)
                    await self.redis.rpush(queue_name, json.dumps(event))
                elif not success:
                    # Dead Letter Queue
                    dlq_key = f"{queue_name}.dlq"
                    await self.redis.rpush(dlq_key, raw_event)
                    logger.error(f"💀 DLQ: {event.get('id', 'unknown')} → {dlq_key}")
                    metrics.inc("worker.dead_letter")

            except Exception as e:
                logger.error(f"❌ Worker loop error: {e}")
                metrics.inc("worker.loop_error")
                await asyncio.sleep(5)


# Production queues
QUEUES = {
    "high_priority": os.getenv("REDIS_QUEUE_HIGH", "kirp_events:high"),
    "normal": os.getenv("REDIS_QUEUE_NORMAL", "kirp_events"),
    "low_priority": os.getenv("REDIS_QUEUE_LOW", "kirp_events:low"),
}

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    worker = EnterpriseWorker(QUEUES)
    asyncio.run(worker.run())
