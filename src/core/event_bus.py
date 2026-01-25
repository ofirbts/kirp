"""
Event Bus — Kafka (prod) / Redis Streams (dev).

Publish events for workers; trigger agents. Provider-agnostic.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


class EventBus:
    """Abstract event bus. Kafka or Redis Streams."""

    def __init__(self) -> None:
        self._provider = (os.getenv("EVENT_BUS_PROVIDER", "redis") or "redis").lower()
        self._redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self._kafka_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
        self._stream_prefix = os.getenv("REDIS_STREAMS_PREFIX", "kirp:")
        self._redis: Any = None
        self._kafka_producer: Any = None

    async def connect(self) -> None:
        if self._provider == "kafka":
            try:
                from aiokafka import AIOKafkaProducer
                self._kafka_producer = AIOKafkaProducer(bootstrap_servers=self._kafka_servers)
                await self._kafka_producer.start()
                logger.info("EventBus connected to Kafka %s", self._kafka_servers)
            except Exception as e:
                logger.error("EventBus Kafka failed: %s", e)
                raise
        else:
            try:
                import redis.asyncio as redis
                self._redis = redis.from_url(self._redis_url, decode_responses=True)
                await self._redis.ping()
                logger.info("EventBus connected to Redis Streams %s", self._redis_url)
            except Exception as e:
                logger.error("EventBus Redis failed: %s", e)
                raise

    async def publish(self, topic: str, payload: dict[str, Any]) -> None:
        """Publish event to topic/stream."""
        if self._provider == "kafka" and self._kafka_producer:
            await self._kafka_producer.send_and_wait(topic, json.dumps(payload).encode("utf-8"))
            logger.debug("EventBus published to Kafka %s", topic)
        elif self._redis:
            stream = f"{self._stream_prefix}{topic}"
            await self._redis.xadd(stream, {"payload": json.dumps(payload)})
            logger.debug("EventBus published to Redis stream %s", stream)

    async def close(self) -> None:
        if self._kafka_producer:
            await self._kafka_producer.stop()
            self._kafka_producer = None
        if self._redis:
            await self._redis.close()
            self._redis = None
