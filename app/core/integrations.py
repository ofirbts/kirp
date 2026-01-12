import os
import logging
from pymongo import MongoClient
import redis
from functools import lru_cache
from app.integrations.whatsapp_gateway import get_whatsapp_gateway

logger = logging.getLogger(__name__)

@lru_cache
def get_mongo_db():
    uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    db_name = os.getenv("MONGO_DB_NAME", "kirp_os")
    client = MongoClient(uri)
    return client[db_name]

@lru_cache
def get_redis_client():
    return redis.Redis(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", 6379)),
        decode_responses=True
    )

# Singleton instances for the app
mongo_db = get_mongo_db()
redis_client = get_redis_client()
wa_gateway = get_whatsapp_gateway()
