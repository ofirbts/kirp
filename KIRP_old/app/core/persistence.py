# app/core/persistence.py
"""
KIRP Unified Persistence Layer
Enterprise-grade MongoDB with pooling, retries, sessions, and full API compatibility.
"""

import logging
import os
import asyncio
from typing import List, Dict, Any, Optional, AsyncGenerator
from datetime import datetime, timezone
from contextlib import asynccontextmanager

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from bson import ObjectId

logger = logging.getLogger(__name__)


class PersistenceManager:
    """Unified MongoDB manager with enterprise features + backward compatibility."""

    _client: Optional[AsyncIOMotorClient] = None
    _db: Optional[AsyncIOMotorDatabase] = None
    _initialized = False

    # ----------------------------------------------------------------------
    # Initialization
    # ----------------------------------------------------------------------
    @classmethod
    async def initialize(cls):
        """Initialize MongoDB connection with production settings."""
        if cls._initialized:
            return

        mongo_uri = os.getenv(
            "MONGO_URI",
            "mongodb://root:example@mongodb:27017/kirp?authSource=admin"
        ).strip()

        cls._client = AsyncIOMotorClient(
            mongo_uri,
            maxPoolSize=50,
            minPoolSize=10,
            maxIdleTimeMS=30000,
            serverSelectionTimeoutMS=5000,
            retryWrites=True,
            retryReads=True,
            heartbeatFrequencyMS=10000,
        )

        cls._db = cls._client.get_default_database()

        # Test connection
        await cls._db.command("ping")
        cls._initialized = True
        logger.info("✅ MongoDB Enterprise connection established")

    @classmethod
    async def get_db(cls) -> AsyncIOMotorDatabase:
        """Get database with auto-initialization."""
        await cls.initialize()
        return cls._db

    # ----------------------------------------------------------------------
    # Session Manager
    # ----------------------------------------------------------------------
    @classmethod
    @asynccontextmanager
    async def session(cls, user_id: str = None) -> AsyncGenerator["PersistenceManager", None]:
        """Enterprise session wrapper."""
        session = cls._client.start_session()
        try:
            if user_id:
                session.user_id = user_id
            yield cls
        finally:
            await session.end_session()

    # ----------------------------------------------------------------------
    # User Management
    # ----------------------------------------------------------------------
    @classmethod
    async def verify_user(cls, username: str, password: str = None) -> Optional[Dict]:
        """User lookup with projection."""
        db = await cls.get_db()
        pipeline = [
            {"$match": {"username": username}},
            {"$project": {"_id": 1, "username": 1, "full_name": 1, "role": 1}},
        ]
        user = await db.users.aggregate(pipeline).to_list(1)
        return user[0] if user else None

    # ----------------------------------------------------------------------
    # Events
    # ----------------------------------------------------------------------
    @classmethod
    async def save_event(
        cls,
        event_type: str,
        data: Dict[str, Any],
        user_id: Optional[str] = None,
    ) -> str:
        """Primary event persistence."""
        db = await cls.get_db()
        event = {
            "event_type": event_type,
            "data": data,
            "user_id": user_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "created_at": datetime.now(timezone.utc),
        }
        result = await db.events.insert_one(event)
        return str(result.inserted_id)

    @classmethod
    async def append_event(cls, event_type: str, data: dict, user_id: Optional[str] = None):
        """Backward-compatible alias."""
        return await cls.save_event(event_type, data, user_id)

    @classmethod
    async def get_user_events(cls, user_id: str) -> List[Dict]:
        """Fetch events for a specific user."""
        db = await cls.get_db()
        cursor = db.events.find(
            {"user_id": user_id},
            projection={"data": 1, "status": 1, "id": 1, "timestamp": 1},
            sort=[("timestamp", -1)],
        ).limit(100)
        return await cursor.to_list(100)

    # ----------------------------------------------------------------------
    # Improvements / Config Changes
    # ----------------------------------------------------------------------
    @classmethod
    async def get_pending_improvements(cls) -> List[Dict[str, Any]]:
        db = await cls.get_db()
        cursor = db.improvements.find(
            {"applied": {"$ne": True}, "dismissed": {"$ne": True}}
        ).sort("created_at", -1)
        return await cursor.to_list(100)

    @classmethod
    async def apply_config_change(cls, imp_id: str) -> None:
        db = await cls.get_db()
        await db.improvements.update_one(
            {"_id": ObjectId(imp_id)},
            {"$set": {"applied": True, "applied_at": datetime.now(timezone.utc)}},
        )

    # ----------------------------------------------------------------------
    # Agent State
    # ----------------------------------------------------------------------
    @classmethod
    async def update_agent_state(cls, agent_id: str, new_memory: Dict[str, Any]):
        db = await cls.get_db()
        await db.agent_states.update_one(
            {"agent_id": agent_id},
            {
                "$set": {
                    "memory": new_memory,
                    "last_updated": datetime.now(timezone.utc),
                }
            },
            upsert=True,
        )

    @classmethod
    async def get_agent_state(cls, agent_id: str) -> Dict[str, Any]:
        db = await cls.get_db()
        state = await db.agent_states.find_one({"agent_id": agent_id})
        return state if state else {"memory": {}, "agent_id": agent_id}

    # ----------------------------------------------------------------------
    # Dashboard / Metrics
    # ----------------------------------------------------------------------
    @classmethod
    async def get_dashboard_metrics(cls, user_id: str) -> Dict[str, Any]:
        db = await cls.get_db()
        pipeline = [
            {"$match": {"user_id": user_id}},
            {
                "$group": {
                    "knowledge_items": {
                        "$sum": {"$cond": [{"$eq": ["$event_type", "knowledge_add"]}, 1, 0]}
                    },
                    "new_insights": {
                        "$sum": {"$cond": [{"$eq": ["$event_type", "insight_generated"]}, 1, 0]}
                    },
                    "active_jobs": {
                        "$sum": {"$cond": [{"$eq": ["$event_type", "job_started"]}, 1, 0]}
                    },
                }
            },
            {"$project": {"knowledge_items": 1, "new_insights": 1, "active_jobs": 1, "active_agents": 1}},
        ]
        result = await db.events.aggregate(pipeline).to_list(1)
        return result[0] if result else {
            "knowledge_items": 0,
            "new_insights": 0,
            "active_jobs": 0,
            "active_agents": 1,
        }

    # ----------------------------------------------------------------------
    # System Health
    # ----------------------------------------------------------------------
    @classmethod
    async def get_system_health(cls) -> Dict[str, Any]:
        db = await cls.get_db()
        collections = await db.list_collection_names()
        events_count = await db.events.count_documents({})
        return {
            "status": "healthy",
            "collections": len(collections),
            "recent_events": events_count,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    # ----------------------------------------------------------------------
    # Sources
    # ----------------------------------------------------------------------
    @classmethod
    async def get_sources(cls) -> List[Dict]:
        db = await cls.get_db()
        cursor = db.sources.find({}, {"_id": 0}).sort("created_at", -1)
        return await cursor.to_list(100)

    # ----------------------------------------------------------------------
    # Jobs
    # ----------------------------------------------------------------------
    @classmethod
    async def get_all_jobs(cls) -> List[Dict]:
        db = await cls.get_db()
        cursor = db.jobs.find(
            {},
            projection={"status": 1, "created_at": 1, "source": 1},
            sort=[("created_at", -1)],
        ).limit(50)
        jobs = await cursor.to_list(50)
        return [
            {"id": str(j.get("_id", "")), **{k: v for k, v in j.items() if k != "_id"}}
            for j in jobs
        ]

    @classmethod
    async def create_job(cls, job_id: str, payload: Dict[str, Any]):
        db = await cls.get_db()
        job = {
            "job_id": job_id,
            "payload": payload,
            "status": "queued",
            "created_at": datetime.now(timezone.utc),
        }
        await db.jobs.insert_one(job)
        return job

    @classmethod
    async def update_job(cls, job_id: str, status: str, progress: float = None, error: str = None):
        db = await cls.get_db()
        update = {"status": status}
        if progress is not None:
            update["progress"] = progress
        if error:
            update["error"] = error

        await db.jobs.update_one({"job_id": job_id}, {"$set": update})

    @classmethod
    async def get_job(cls, job_id: str) -> Optional[Dict[str, Any]]:
        db = await cls.get_db()
        return await db.jobs.find_one({"job_id": job_id})

    @classmethod
    async def get_pending_approvals(cls):
        db = await cls.get_db()
        cursor = db.events.find(
            {"status": "pending"},
            sort=[("timestamp", -1)]
        )
        return await cursor.to_list(length=100)


    @classmethod
    async def update_event_status(cls, event_id: str, status: str):
        db = await cls.get_db()
        await db.events.update_one(
            {"_id": ObjectId(event_id)},
            {"$set": {"status": status}}
        )


    @classmethod
    async def get_all_events(cls, limit: int = 50):
        db = await cls.get_db()
        cursor = db.events.find().sort("timestamp", -1).limit(limit)
        return await cursor.to_list(length=limit)

# Auto-initialize on import
asyncio.create_task(PersistenceManager.initialize())
