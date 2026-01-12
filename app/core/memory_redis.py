import time
import hashlib
import json
from typing import List, Dict, Any
from app.core.redis_client import get_redis


class RedisMemory:
    """
    Short-term / recent memory for UI, timeline, WhatsApp.
    """

    SHORT_TTL = 60 * 60 * 24        # 24h
    RECENT_TTL = 60 * 60 * 24 * 7   # 7d

    def __init__(self):
        self.redis = get_redis()

    # ---------- Keys ----------

    def _recent_key(self) -> str:
        return "kirp:memory:recent"

    def _hash_key(self) -> str:
        return "kirp:memory:hashes"

    # ---------- Helpers ----------

    def _hash(self, text: str) -> str:
        return hashlib.sha256(text.strip().encode()).hexdigest()

    # ---------- Write ----------

    def add(self, content: str, session_id: str = "default") -> bool:
        content = content.strip()
        if not content:
            return False

        h = self._hash(content)

        # global dedup
        if self.redis.sismember(self._hash_key(), h):
            return False

        item = {
            "type": "memory",
            "text": content,
            "ts": int(time.time()),
            "session_id": session_id,
            "source": "redis",
        }

        payload = json.dumps(item)

        self.redis.lpush(self._recent_key(), payload)
        self.redis.expire(self._recent_key(), self.RECENT_TTL)

        self.redis.sadd(self._hash_key(), h)

        return True

    # ---------- Read ----------

    def get_recent(self, limit: int = 10) -> List[Dict[str, Any]]:
        raw = self.redis.lrange(self._recent_key(), 0, limit - 1)
        return [json.loads(x) for x in raw]

    # ---------- Debug ----------

    def debug_info(self) -> Dict[str, Any]:
        return {
            "recent_count": self.redis.llen(self._recent_key()),
            "hashes_count": self.redis.scard(self._hash_key()),
        }
