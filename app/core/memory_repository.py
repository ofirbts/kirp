import time
import uuid
from typing import Dict, List, Any
from app.infra.redis_client import get_redis


class MemoryRepository:
    PREFIX = "memory:"

    def __init__(self):
        self.redis = get_redis()

    def add(self, content: str, source: str, tier: str) -> str:
        memory_id = str(uuid.uuid4())
        key = self.PREFIX + memory_id

        data = {
            "id": memory_id,
            "content": content,
            "source": source,
            "tier": tier,
            "created_at": time.time(),
        }

        self.redis.hset(key, mapping=data)
        self.redis.incr("stats:total_memories")

        return memory_id

    def get(self, memory_id: str) -> Dict[str, Any]:
        return self.redis.hgetall(self.PREFIX + memory_id)

    def recent(self, limit: int = 20) -> List[Dict[str, Any]]:
        ids = self.redis.lrange("memories:recent", 0, limit - 1)
        return [self.get(mid) for mid in ids]

    def stats(self) -> Dict[str, Any]:
        return {
            "total_memories": int(self.redis.get("stats:total_memories") or 0),
        }
