import os
import logging
from pymongo import MongoClient
import redis
from functools import lru_cache
from app.integrations.whatsapp_gateway import get_whatsapp_gateway

logger = logging.getLogger(__name__)

@lru_cache
def get_mongo_db_instance():
    # שלב 1: משיכת ה-URI וניקוי תווים נסתרים (למניעת שגיאת ה-27017\r)
    uri = os.getenv("MONGO_URI", "mongodb://root:example@localhost:27017").strip()
    db_name = os.getenv("MONGO_DB_NAME", "kirp").strip()
    
    # שלב 2: יצירת החיבור
    client = MongoClient(uri)
    return client[db_name]

@lru_cache
def get_redis_client():
    return redis.Redis(
        host=os.getenv("REDIS_HOST", "localhost").strip(),
        port=int(os.getenv("REDIS_PORT", 6379)),
        decode_responses=True
    )

# --- Singleton instances (אלו המשתנים ששאר האפליקציה מייבאת) ---
mongo_db = get_mongo_db_instance()
redis_client = get_redis_client()
wa_gateway = get_whatsapp_gateway()