import logging
import time
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timezone
from app.models.schemas import Insight, IngestionJob
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class PersistenceManager:
    _client = None
    _db = None

    @classmethod
    async def get_db(cls):
        if cls._db is None:
            # שימוש ב-URI מה-.env ששלחת
            mongo_uri = "mongodb://root:example@mongodb:27017/kirp?authSource=admin"
            cls._client = AsyncIOMotorClient(mongo_uri)
            cls._db = cls._client["kirp"]
        return cls._db

    @classmethod
    async def get_system_health(cls) -> Dict[str, Any]:
        """סעיף 1.4: מדידת זמני תגובה של רכיבי הליבה"""
        db = await cls.get_db()
        start = time.time()
        try:
            # בדיקת latency של MongoDB
            await db.command("ping")
            mongo_latency = int((time.time() - start) * 1000)
            return {
                "mongodb": {"latency": f"{mongo_latency}ms", "status": "healthy"},
                "vector_store": {"latency": "45ms", "status": "healthy"}, # דמי כרגע
                "llm": {"latency": "234ms", "status": "healthy"} # דמי כרגע
            }
        except Exception as e:
            logger.error(f"❌ Health Check Failed: {e}")
            return {"mongodb": {"status": "unhealthy", "error": str(e)}}

    @classmethod
    async def save_insight(cls, user_id: str, insight: Insight):
        """שמירת תובנה חדשה שנוצרה על ידי ה-Intelligence Engine"""
        db = await cls.get_db()
        await db.insights.insert_one({
            "user_id": user_id,
            **insight.model_dump()
        })

    @classmethod
    async def get_user_insights(cls, user_id: str) -> List[Dict]:
        """שליפת כל התובנות עבור ה-Dashboard"""
        db = await cls.get_db()
        cursor = db.insights.find({"user_id": user_id}).sort("created_at", -1)
        return await cursor.to_list(length=100)

    @classmethod
    async def update_job_status(cls, job: IngestionJob):
        """סעיף 2: עדכון מצב עיבוד של קובץ/מקור מידע"""
        db = await cls.get_db()
        await db.jobs.update_one(
            {"id": job.id},
            {"$set": job.model_dump()},
            upsert=True
        )