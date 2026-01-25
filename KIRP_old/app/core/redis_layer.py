import redis
import os

redis_client = redis.Redis(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=6379,
    decode_responses=True
)

def cache_get(key):
    return redis_client.get(key)

def cache_set(key, value, ttl=60):
    redis_client.setex(key, ttl, value)
