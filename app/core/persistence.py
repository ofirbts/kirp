import logging
import os
import time
import uuid
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from pymongo import MongoClient
from app.models.schemas import Insight, IngestionJob, KnowledgeItem
from bson import ObjectId

logger = logging.getLogger(__name__)

# פונקציית עזר סינכרונית עבור רכיבי ה-Auth
def get_sync_db():
    mongo_uri = os.getenv("MONGO_URI", "mongodb://root:example@mongodb:27017/")
    client = MongoClient(mongo_uri)
    return client["kirp"]

class PersistenceManager:
    _client = None
    _db = None

    @classmethod
    async def get_db(cls):
        """מנהל חיבור יחיד (Singleton) למסד הנתונים"""
        if cls._db is None:
            mongo_uri = os.getenv("MONGO_URI", "mongodb://root:example@mongodb:27017/").strip()
            cls._client = AsyncIOMotorClient(mongo_uri)
            try:
                # ניסיון לקבל DB ספציפי מה-URI, אם לא קיים - ברירת מחדל
                cls._db = cls._client.get_default_database()
            except Exception:
                cls._db = cls._client["kirp"]
        return cls._db
    @classmethod
    async def save_event(cls, event_type: str, data: Dict[str, Any]):
        """
        מתודה גנרית לרישום אירועים. 
        פותרת את הצורך בפונקציה ייעודית לכל עדכון קטן.
        """
        db = await cls.get_db()
        
        # הכנת האובייקט לשמירה בלוג הכללי
        event_entry = {
            "event_type": event_type,
            "data": data,
            "processed": False,
            "created_at": datetime.now(timezone.utc)
        }
        
        # ניתוב חכם: אם זה ידע מקצועי, נשמור גם באוסף הייעודי
        if event_type == "knowledge_add":
            await db.knowledge.insert_one({
                "content": data.get("text") or data.get("content"),
                "user_id": data.get("user_id", "system"),
                "metadata": data.get("metadata", {}),
                "created_at": datetime.now(timezone.utc)
            })
            
        return await db.events.insert_one(event_entry)

    @classmethod
    async def save_knowledge_item(cls, user_id: str, item: KnowledgeItem):
        """שמירת פריט ידע מובנה (Pydantic Model)"""
        db = await cls.get_db()
        await db.knowledge.insert_one({
            "user_id": user_id,
            **item.model_dump(),
            "created_at": datetime.now(timezone.utc)
        })

    @classmethod
    async def save_technical_improvement(cls, improvement: Dict[str, Any]):
        """שמירת הצעות לשיפור מה-Intelligence Layer"""
        db = await cls.get_db()
        improvement["created_at"] = datetime.now(timezone.utc)
        improvement["applied"] = False
        await db.improvements.insert_one(improvement)
    
    # --- Dashboard & Monitoring ---
    @classmethod
    async def get_dashboard_metrics(cls, user_id: str) -> Dict[str, Any]:
        """חישוב מדדים בזמן אמת עבור ה-UI"""
        db = await cls.get_db()
        return {
            "knowledge_items": await db.knowledge.count_documents({"user_id": user_id}),
            "active_agents": await db.agents.count_documents({"status": "active"}),
            "new_insights": await db.insights.count_documents({"user_id": user_id, "status": "new"}),
            "active_jobs": await db.jobs.count_documents({"status": {"$ne": "DONE"}})
        }

    @classmethod
    async def get_system_health(cls) -> Dict[str, Any]:
        """בדיקת זמינות וזמני תגובה של רכיבי התשתית"""
        db = await cls.get_db()
        start = time.time()
        try:
            await db.command("ping")
            latency = int((time.time() - start) * 1000)
            return {
                "mongodb": {"latency": f"{latency}ms", "status": "healthy"},
                "vector_store": {"latency": "45ms", "status": "healthy"}, # דמי לצורך ה-UI
                "llm": {"latency": "234ms", "status": "healthy"}         # דמי לצורך ה-UI
            }
        except Exception as e:
            logger.error(f"❌ Health Check Failed: {e}")
            return {"mongodb": {"status": "unhealthy", "error": str(e)}}

    # --- Agent & Job Management ---
    @classmethod
    async def update_agent_state(cls, agent_id: str, new_memory: Dict[str, Any]):
        """עדכון הזיכרון והמצב של סוכן חכם"""
        db = await cls.get_db()
        await db.agent_states.update_one(
            {"agent_id": agent_id},
            {"$set": {
                "memory": new_memory,
                "last_updated": datetime.now(timezone.utc)
            }},
            upsert=True
        )

    @classmethod
    async def update_job_status(cls, job: IngestionJob):
        """עדכון סטטוס תהליך הזרקת נתונים"""
        db = await cls.get_db()
        await db.jobs.update_one(
            {"id": job.id},
            {"$set": job.model_dump()},
            upsert=True
        )

    # --- Auth & User Management (Async) ---
    @classmethod
    async def get_user_by_email(cls, email: str) -> Optional[Dict]:
        db = await cls.get_db()
        return await db.users.find_one({"email": email})

    @classmethod
    async def create_google_user(cls, email: str, full_name: str, avatar_url: str):
        """יצירה או עדכון משתמש OAuth"""
        db = await cls.get_db()
        now = datetime.now(timezone.utc)
        return await db.users.update_one(
            {"email": email},
            {
                "$set": {
                    "full_name": full_name,
                    "avatar_url": avatar_url,
                    "last_login": now,
                    "updated_at": now
                },
                "$setOnInsert": {
                    "created_at": now,
                    "role": "user"
                }
            },
            upsert=True
        )

    # --- Static Methods for Legacy Sync Auth ---
    @staticmethod
    def verify_user(username: str, password: str = None) -> Optional[Dict]:
        """בדיקת משתמש (סינכרוני) עבור מערכת ה-Login הישנה"""
        db = get_sync_db()
        user = db["users"].find_one({"username": username})
        if user:
            user["_id"] = str(user["_id"])
        return user
        
    @classmethod
    async def get_agent_state(cls, agent_id: str) -> Dict[str, Any]:
        """שליפת מצב הסוכן (זיכרון) - נדרש עבור /query"""
        db = await cls.get_db()
        state = await db.agent_states.find_one({"agent_id": agent_id})
        if not state:
            return {"memory": {}, "agent_id": agent_id}
        return state

    @classmethod
    async def get_all_jobs(cls) -> List[Dict[str, Any]]:
        """שליפת כל תהליכי ההזרקה - נדרש עבור /jobs/all"""
        db = await cls.get_db()
        cursor = db.jobs.find().sort("created_at", -1)
        jobs = await cursor.to_list(length=100)
        for job in jobs:
            job["_id"] = str(job["_id"]) # המרה ל-String עבור JSON
        return jobs

    def get_sources(self):
        return list(self.db.sources.find())

    def get_agents_stats(self):
        # מחזיר אגרגציה של פעולות סוכנים מה-events או טבלת agents
        return list(self.db.agents.find())

    @staticmethod
    async def get_pending_improvements() -> List[Dict[str, Any]]:
        """
        מחזיר שיפורים שעדיין לא יושמו ולא בוטלו.
        """
        db = await PersistenceManager.get_db()
        cursor = db.improvements.find(
            {
                "applied": {"$ne": True},
                "dismissed": {"$ne": True},
            }
        ).sort("created_at", -1)
        return await cursor.to_list(200)

    @classmethod
    async def apply_config_change(cls, imp_id: str) -> None:
        """
        מיישם שינוי קונפיגורציה לפי improvement.
        כאן אפשר לחבר ל־config collection / feature flags / וכו'.
        כרגע – רק מסמן כ-applied.
        """
        db = await cls.get_db()
        try:
            oid = ObjectId(imp_id)
        except Exception:
            raise ValueError("Invalid improvement id")

        imp = await db.improvements.find_one({"_id": oid})
        if not imp:
            raise ValueError("Improvement not found")

        # כאן בעתיד: ליישם את השינוי בפועל (config, feature flags וכו')

        await db.improvements.update_one(
            {"_id": oid},
            {"$set": {
                "applied": True,
                "applied_at": datetime.now(timezone.utc),
            }}
        )
    @classmethod
    async def append_event(cls, event_type: str, payload: dict, level: str = "INFO"):
        # הופכים את זה לעקבי עם save_event
        db = await cls.get_db()
        event = {
            "event_type": event_type,
            "data": payload, 
            "level": level,
            "processed": False,
            "created_at": datetime.now(timezone.utc)
        }
        await db.events.insert_one(event)