"""
Unified Idempotency Provider — Dual-layer idempotency checking (Redis hot cache + Mongo persistent store).
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from src.core.registry import get_registry

logger = logging.getLogger(__name__)

IDEMPOTENCY_TTL_SEC = 3600  # 1 hour


class IdempotencyProvider:
    """
    Unified idempotency checker.
    Checks Redis first, falls back to MongoDB.
    Stores in both to ensure reliability and durability.
    """

    def __init__(self) -> None:
        self.registry = get_registry()

    def _redis_key(self, tenant_id: str, unique_key: str) -> str:
        return f"idempotency:{tenant_id}:{unique_key}"

    async def get(self, tenant_id: str, unique_key: str) -> str | None:
        """
        Check if the unique key has already been processed for this tenant.
        Returns the stored value (e.g. event_id) if exists, or None.
        """
        if not tenant_id or not unique_key:
            return None

        redis_key = self._redis_key(tenant_id, unique_key)

        # 1. Try Redis
        try:
            r = self.registry.get_redis_async()
            val = await r.get(redis_key)
            if val is not None:
                logger.info("Idempotency cache hit (Redis): %s", redis_key)
                return str(val)
        except Exception as e:
            logger.warning("Idempotency Redis check failed: %s", e)

        # 2. Try MongoDB fallback
        try:
            db = await self.registry.get_mongo_db()
            doc = await db.idempotency.find_one({"tenant_id": tenant_id, "key": unique_key})
            if doc:
                logger.info("Idempotency store hit (Mongo): tenant=%s key=%s", tenant_id, unique_key)
                val_str = str(doc.get("value", "1"))
                # Write back to Redis to re-populate the cache
                try:
                    r = self.registry.get_redis_async()
                    await r.setex(redis_key, IDEMPOTENCY_TTL_SEC, val_str)
                except Exception:
                    pass
                return val_str
        except Exception as e:
            logger.warning("Idempotency Mongo check failed: %s", e)

        return None

    async def record(self, tenant_id: str, unique_key: str, value: str = "1") -> None:
        """
        Record that a unique key has been processed, storing the given value.
        """
        if not tenant_id or not unique_key:
            return

        redis_key = self._redis_key(tenant_id, unique_key)

        # 1. Store in Redis
        try:
            r = self.registry.get_redis_async()
            await r.setex(redis_key, IDEMPOTENCY_TTL_SEC, value)
        except Exception as e:
            logger.warning("Idempotency Redis record failed: %s", e)

        # 2. Store in MongoDB
        try:
            db = await self.registry.get_mongo_db()
            await db.idempotency.update_one(
                {"tenant_id": tenant_id, "key": unique_key},
                {
                    "$set": {
                        "tenant_id": tenant_id,
                        "key": unique_key,
                        "value": value,
                        "updated_at": datetime.now(timezone.utc),
                    }
                },
                upsert=True,
            )
        except Exception as e:
            logger.warning("Idempotency Mongo record failed: %s", e)


_provider = IdempotencyProvider()


def get_idempotency_provider() -> IdempotencyProvider:
    return _provider
