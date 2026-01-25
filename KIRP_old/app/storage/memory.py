# app/services/memory_storage.py
"""
KIRP Unified Memory Storage v7
- Logical "memories" collection (strength, recency)
- Semantic search via vector store
- Analytics via events
"""

from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional

from app.models.memory import MemoryRecord
from app.core.persistence import PersistenceManager
from app.rag.vector_store import search_vectors


class MemoryStorage:
    """Production memory management + semantic search"""

    # ---------- Low-level document storage (memories collection) ----------

    @staticmethod
    async def _collection():
        db = await PersistenceManager.get_db()
        return db["memories"]

    @classmethod
    async def save_memory(cls, record: MemoryRecord) -> None:
        """
        Upsert-like behavior:
        - If same memory_type + content exists → increment strength
        - Else → insert new record
        """
        collection = await cls._collection()
        existing = await collection.find_one(
            {
                "memory_type": record.memory_type,
                "content": record.content,
            }
        )

        if existing:
            await collection.update_one(
                {"_id": existing["_id"]},
                {
                    "$inc": {"strength": 1},
                    "$set": {"last_updated": datetime.now(timezone.utc)},
                },
            )
        else:
            await collection.insert_one(record.dict())

    @classmethod
    async def fetch_recent_memories(cls, limit: int = 20) -> List[MemoryRecord]:
        collection = await cls._collection()
        cursor = (
            collection.find()
            .sort("created_at", -1)
            .limit(limit)
        )
        return [MemoryRecord(**doc) async for doc in cursor]

    @classmethod
    async def fetch_memories_by_days(cls, days: int) -> List[MemoryRecord]:
        collection = await cls._collection()
        since = datetime.now(timezone.utc) - timedelta(days=days)
        cursor = collection.find({"created_at": {"$gte": since}})
        return [MemoryRecord(**doc) async for doc in cursor]

    @classmethod
    async def fetch_relevant_memories(cls, limit: int = 20) -> List[MemoryRecord]:
        """
        Return memories with strength > 0, ordered by strength desc.
        """
        collection = await cls._collection()
        cursor = (
            collection.find({"strength": {"$gt": 0}})
            .sort("strength", -1)
            .limit(limit)
        )
        return [MemoryRecord(**doc) async for doc in cursor]

    # ---------- High-level semantic layer ----------

    @staticmethod
    async def add_memory(
        text: str,
        user_id: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Add memory via ingestion pipeline (vector store + events).
        """
        from app.services.pipeline import ingest_text

        result = await ingest_text(
            text=text,
            source="memory_storage",
            metadata=metadata or {},
            user_id=user_id,
        )
        return result

    @staticmethod
    async def search_memories(
        query: str,
        user_id: str,
        k: int = 6,
    ) -> List[Dict[str, Any]]:
        """
        Semantic memory search via vector store.
        """
        return await search_vectors(query, k=k, user_id=user_id)

    @staticmethod
    async def get_memory_stats(user_id: str) -> Dict[str, int]:
        """
        Memory analytics based on events.
        """
        db = await PersistenceManager.get_db()
        pipeline = [
            {"$match": {"data.user_id": user_id}},
            {
                "$group": {
                    "_id": "$event_type",
                    "count": {"$sum": 1},
                }
            },
        ]
        results = await db.events.aggregate(pipeline).to_list(None)
        return {r["_id"]: r["count"] for r in results}
