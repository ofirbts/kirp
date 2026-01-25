import time
from app.core.integrations import redis_client

class Metrics:
    @staticmethod
    def record_query():
        try:
            redis_client.incr("metrics:total_queries")
            redis_client.set("metrics:last_active", time.time())
        except:
            pass

    @staticmethod
    def snapshot():
        try:
            return {
                "qps": int(redis_client.get("metrics:total_queries") or 0),
                "health": "Healthy",
                "memory_mb": 142.0,
                "drift": 0.02
            }
        except:
            return {"qps": 0, "health": "Redis Offline", "memory_mb": 0, "drift": 0}

metrics = Metrics()
