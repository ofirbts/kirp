# app/services/jobs.py
"""
KIRP Unified Job Storage v7
Production job queue + status tracking
"""

import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from enum import Enum

from app.core.persistence import PersistenceManager


class JobPriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"


class JobStorage:
    """Unified production job persistence layer"""

    @staticmethod
    async def create_job(
        source: str,
        task: str,
        user_id: str,
        priority: JobPriority = JobPriority.NORMAL,
    ) -> str:
        job_id = str(uuid.uuid4())
        job_data = {
            "id": job_id,
            "source": source,
            "task": task,
            "status": "pending",
            "priority": priority.value,
            "user_id": user_id,
            "progress": 0.0,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }

        db = await PersistenceManager.get_db()
        await db.jobs.insert_one(job_data)
        return job_id

    @staticmethod
    async def update_status(
        job_id: str,
        status: str,
        progress: Optional[float] = None,
    ) -> bool:
        db = await PersistenceManager.get_db()
        update_data = {
            "status": status,
            "updated_at": datetime.now(timezone.utc),
        }
        if progress is not None:
            update_data["progress"] = progress

        result = await db.jobs.update_one(
            {"id": job_id},
            {"$set": update_data},
        )
        return result.modified_count > 0

    @staticmethod
    async def get_user_jobs(user_id: str, limit: int = 50) -> List[Dict]:
        db = await PersistenceManager.get_db()
        cursor = db.jobs.find(
            {"user_id": user_id},
            sort=[("created_at", -1)],
            limit=limit,
        )
        return await cursor.to_list(length=limit)

    @staticmethod
    async def get_all_jobs(limit: int = 100) -> List[Dict]:
        db = await PersistenceManager.get_db()
        cursor = db.jobs.find(
            {},
            sort=[("created_at", -1)],
            limit=limit,
            projection={"task": 0},  # hide full task text
        )
        return await cursor.to_list(length=limit)
