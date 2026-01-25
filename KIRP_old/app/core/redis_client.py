"""
Simple Redis client stub
"""
import redis.asyncio as redis

async def get_redis():
    """Production Redis client"""
    return redis.Redis.from_url("redis://localhost:6379/0")
