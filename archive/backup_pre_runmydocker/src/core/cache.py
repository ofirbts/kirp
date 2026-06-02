"""
Caching Layer — Redis-based caching for performance.

Caches:
- Schema nodes (TTL: 5 minutes)
- RAG results (TTL: 1 minute)
- Agent results (TTL: 2 minutes)
"""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

from src.core.integrations import get_redis_async

logger = logging.getLogger(__name__)

# Cache TTLs (seconds)
CACHE_TTL_SCHEMA = 300  # 5 minutes
CACHE_TTL_RAG = 60  # 1 minute
CACHE_TTL_AGENT = 120  # 2 minutes


def _cache_key(prefix: str, tenant_id: str, *args: Any) -> str:
    """Generate cache key."""
    key_parts = [prefix, tenant_id] + [str(a) for a in args]
    key_str = ":".join(key_parts)
    # Hash if too long
    if len(key_str) > 200:
        key_str = f"{prefix}:{tenant_id}:{hashlib.sha256(key_str.encode()).hexdigest()}"
    return f"cache:{key_str}"


async def get_cached(key: str) -> Any | None:
    """Get value from cache."""
    try:
        redis = await get_redis_async()
        if redis:
            value = await redis.get(key)
            if value:
                return json.loads(value)
    except Exception as e:
        logger.debug("Cache get failed: %s", e)
    return None


async def set_cached(key: str, value: Any, ttl: int) -> None:
    """Set value in cache with TTL."""
    try:
        redis = await get_redis_async()
        if redis:
            await redis.setex(key, ttl, json.dumps(value))
    except Exception as e:
        logger.debug("Cache set failed: %s", e)


async def invalidate_cache(prefix: str, tenant_id: str) -> None:
    """Invalidate all cache entries for a prefix and tenant."""
    try:
        redis = await get_redis_async()
        if redis:
            pattern = f"cache:{prefix}:{tenant_id}:*"
            # Note: Redis SCAN would be better for production
            # For now, just log
            logger.debug("Cache invalidation requested: %s", pattern)
    except Exception as e:
        logger.debug("Cache invalidation failed: %s", e)
