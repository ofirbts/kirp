"""
M3 IdentityOS — MongoDB-backed memory store (optional).

Set M3_MEMORY_BACKEND=mongo and MONGO_URI to persist M3 data across restarts.
Collections: m3_reflections, m3_micro_actions, m3_weekly_synthesis, m3_monthly_evolution,
m3_identity_profiles, m3_gap_snapshots. All queries filter by tenant_id and user_id.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from src.modules.m3.memory import (
    M3MemoryStore,
    IdentityProfile,
    ReflectionEntry,
    MicroAction,
    WeeklySynthesis,
    MonthlyEvolution,
    GapSnapshot,
)

logger = logging.getLogger(__name__)


def _serialize_dt(dt: datetime | None) -> Any:
    """Mongo accepts datetime; return as-is for BSON."""
    return dt


def _doc_to_reflection(doc: dict[str, Any]) -> ReflectionEntry:
    return ReflectionEntry(
        user_id=doc["user_id"],
        tenant_id=doc["tenant_id"],
        space_id=doc["space_id"],
        reflection_date=doc.get("reflection_date", ""),
        reflection_text=doc.get("reflection_text", ""),
        pillar_scores=doc.get("pillar_scores", {}),
        mood=doc.get("mood", ""),
        embedding=doc.get("embedding", []),
        source_event_id=doc.get("source_event_id"),
        created_at=doc.get("created_at"),
        id=doc.get("id", doc.get("_id", "")),
    )


class MongoM3MemoryStore(M3MemoryStore):
    """M3 memory persisted in MongoDB. Same interface as M3MemoryStore."""

    def __init__(self, mongo_uri: str, db_name: str = "kirp") -> None:
        super().__init__()
        self._mongo_uri = mongo_uri
        self._db_name = db_name
        self._client: Any = None
        self._db: Any = None

    async def connect(self) -> None:
        if self._db is not None:
            return
        try:
            from motor.motor_asyncio import AsyncIOMotorClient
            self._client = AsyncIOMotorClient(self._mongo_uri)
            self._db = self._client[self._db_name]
            await self._db.command("ping")
            logger.info("MongoM3MemoryStore connected to MongoDB")
        except Exception as e:
            logger.error("MongoM3MemoryStore connection failed: %s", e)
            raise

    async def _ensure_db(self) -> Any:
        if self._db is None:
            await self.connect()
        return self._db

    async def get_identity_profile(self, tenant_id: str, user_id: str) -> IdentityProfile | None:
        db = await self._ensure_db()
        doc = await db.m3_identity_profiles.find_one({"tenant_id": tenant_id, "user_id": user_id})
        if not doc:
            return None
        return IdentityProfile(
            user_id=doc["user_id"],
            tenant_id=doc["tenant_id"],
            space_id=doc["space_id"],
            identity_vector=doc.get("identity_vector", []),
            pillar_scores=doc.get("pillar_scores", {}),
            ideal_self_vector=doc.get("ideal_self_vector"),
            updated_at=doc.get("updated_at"),
            source_event_id=doc.get("source_event_id"),
        )

    async def upsert_identity_profile(
        self,
        tenant_id: str,
        user_id: str,
        space_id: str,
        identity_vector: list[float],
        pillar_scores: dict[str, float],
        source_event_id: str | None = None,
        ideal_self_vector: list[float] | None = None,
    ) -> None:
        db = await self._ensure_db()
        now = datetime.now(timezone.utc)
        await db.m3_identity_profiles.update_one(
            {"tenant_id": tenant_id, "user_id": user_id},
            {"$set": {
                "tenant_id": tenant_id,
                "user_id": user_id,
                "space_id": space_id,
                "identity_vector": identity_vector,
                "pillar_scores": pillar_scores,
                "ideal_self_vector": ideal_self_vector,
                "updated_at": now,
                "source_event_id": source_event_id,
            }},
            upsert=True,
        )

    async def list_reflections(
        self,
        tenant_id: str,
        user_id: str,
        limit: int = 50,
        before_date: str | None = None,
        since_date: str | None = None,
    ) -> list[ReflectionEntry]:
        db = await self._ensure_db()
        q: dict[str, Any] = {"tenant_id": tenant_id, "user_id": user_id}
        if since_date:
            q["reflection_date"] = q.get("reflection_date", {})
            if isinstance(q["reflection_date"], dict):
                q["reflection_date"]["$gte"] = since_date
            else:
                q["reflection_date"] = {"$gte": since_date}
        if before_date:
            if "reflection_date" in q and isinstance(q["reflection_date"], dict):
                q["reflection_date"]["$lte"] = before_date
            else:
                q["reflection_date"] = {"$lte": before_date}
        cursor = db.m3_reflections.find(q).sort("reflection_date", -1).limit(limit)
        out = []
        async for doc in cursor:
            doc["id"] = doc.get("id") or str(doc.get("_id", ""))
            out.append(_doc_to_reflection(doc))
        return out

    async def append_reflection(
        self,
        tenant_id: str,
        user_id: str,
        space_id: str,
        reflection_date: str,
        reflection_text: str,
        pillar_scores: dict[str, float] | None = None,
        mood: str = "",
        source_event_id: str | None = None,
        embedding: list[float] | None = None,
    ) -> ReflectionEntry:
        from uuid import uuid4
        db = await self._ensure_db()
        now = datetime.now(timezone.utc)
        id_ = str(uuid4())
        doc = {
            "id": id_,
            "tenant_id": tenant_id,
            "user_id": user_id,
            "space_id": space_id,
            "reflection_date": reflection_date,
            "reflection_text": reflection_text,
            "pillar_scores": pillar_scores or {},
            "mood": mood,
            "embedding": embedding or [],
            "source_event_id": source_event_id,
            "created_at": now,
        }
        await db.m3_reflections.insert_one(doc)
        return _doc_to_reflection(doc)

    async def update_last_reflection_classification(
        self,
        tenant_id: str,
        user_id: str,
        pillar_scores: dict[str, float],
        mood: str = "",
    ) -> bool:
        """Update the most recent reflection for this user with classifier output. Returns True if updated."""
        db = await self._ensure_db()
        doc = await db.m3_reflections.find_one(
            {"tenant_id": tenant_id, "user_id": user_id},
            sort=[("created_at", -1)],
        )
        if not doc:
            return False
        await db.m3_reflections.update_one(
            {"_id": doc["_id"]},
            {"$set": {"pillar_scores": pillar_scores or {}, "mood": mood or ""}},
        )
        return True

    async def list_micro_actions(
        self,
        tenant_id: str,
        user_id: str,
        status: str | None = None,
        limit: int = 100,
    ) -> list[MicroAction]:
        db = await self._ensure_db()
        q: dict[str, Any] = {"tenant_id": tenant_id, "user_id": user_id}
        if status:
            q["status"] = status
        cursor = db.m3_micro_actions.find(q).limit(limit)
        out = []
        async for doc in cursor:
            out.append(MicroAction(
                action_id=doc.get("action_id", ""),
                user_id=doc["user_id"],
                tenant_id=doc["tenant_id"],
                space_id=doc["space_id"],
                title=doc.get("title", ""),
                pillar=doc.get("pillar", ""),
                status=doc.get("status", "pending"),
                due_by=doc.get("due_by"),
                roi_score=float(doc.get("roi_score", 0)),
                source_event_id=doc.get("source_event_id"),
                completed_at=doc.get("completed_at"),
                feedback=doc.get("feedback", ""),
            ))
        return out

    async def upsert_micro_action(
        self,
        tenant_id: str,
        user_id: str,
        space_id: str,
        action_id: str,
        title: str,
        pillar: str = "",
        status: str = "pending",
        due_by: str | None = None,
        roi_score: float = 0.0,
        source_event_id: str | None = None,
        completed_at: str | None = None,
        feedback: str = "",
    ) -> None:
        db = await self._ensure_db()
        await db.m3_micro_actions.update_one(
            {"action_id": action_id, "tenant_id": tenant_id, "user_id": user_id},
            {"$set": {
                "tenant_id": tenant_id,
                "user_id": user_id,
                "space_id": space_id,
                "action_id": action_id,
                "title": title,
                "pillar": pillar,
                "status": status,
                "due_by": due_by,
                "roi_score": roi_score,
                "source_event_id": source_event_id,
                "completed_at": completed_at,
                "feedback": feedback,
            }},
            upsert=True,
        )

    async def list_weekly_syntheses(
        self,
        tenant_id: str,
        user_id: str,
        limit: int = 24,
    ) -> list[WeeklySynthesis]:
        db = await self._ensure_db()
        cursor = db.m3_weekly_synthesis.find(
            {"tenant_id": tenant_id, "user_id": user_id}
        ).sort("week_start", -1).limit(limit)
        out = []
        async for doc in cursor:
            out.append(WeeklySynthesis(
                synthesis_id=doc.get("synthesis_id", ""),
                user_id=doc["user_id"],
                tenant_id=doc["tenant_id"],
                space_id=doc["space_id"],
                week_start=doc.get("week_start", ""),
                week_end=doc.get("week_end", ""),
                summary=doc.get("summary", ""),
                pillar_trends=doc.get("pillar_trends", {}),
                insights=doc.get("insights", []),
                source_event_id=doc.get("source_event_id"),
                created_at=doc.get("created_at"),
            ))
        return out

    async def append_weekly_synthesis(
        self,
        tenant_id: str,
        user_id: str,
        space_id: str,
        synthesis_id: str,
        week_start: str,
        week_end: str,
        summary: str,
        pillar_trends: dict[str, Any] | None = None,
        insights: list[str] | None = None,
        source_event_id: str | None = None,
    ) -> None:
        db = await self._ensure_db()
        now = datetime.now(timezone.utc)
        await db.m3_weekly_synthesis.insert_one({
            "synthesis_id": synthesis_id,
            "tenant_id": tenant_id,
            "user_id": user_id,
            "space_id": space_id,
            "week_start": week_start,
            "week_end": week_end,
            "summary": summary,
            "pillar_trends": pillar_trends or {},
            "insights": insights or [],
            "source_event_id": source_event_id,
            "created_at": now,
        })

    async def list_monthly_evolutions(
        self,
        tenant_id: str,
        user_id: str,
        limit: int = 12,
    ) -> list[MonthlyEvolution]:
        db = await self._ensure_db()
        cursor = db.m3_monthly_evolution.find(
            {"tenant_id": tenant_id, "user_id": user_id}
        ).sort("month", -1).limit(limit)
        out = []
        async for doc in cursor:
            out.append(MonthlyEvolution(
                evolution_id=doc.get("evolution_id", ""),
                user_id=doc["user_id"],
                tenant_id=doc["tenant_id"],
                space_id=doc["space_id"],
                month=doc.get("month", ""),
                trajectory=doc.get("trajectory", []),
                new_goals=doc.get("new_goals", []),
                pillar_shifts=doc.get("pillar_shifts", {}),
                source_event_id=doc.get("source_event_id"),
                created_at=doc.get("created_at"),
            ))
        return out

    async def append_monthly_evolution(
        self,
        tenant_id: str,
        user_id: str,
        space_id: str,
        evolution_id: str,
        month: str,
        trajectory: list[dict[str, Any]],
        new_goals: list[str] | None = None,
        pillar_shifts: dict[str, Any] | None = None,
        source_event_id: str | None = None,
    ) -> None:
        db = await self._ensure_db()
        now = datetime.now(timezone.utc)
        await db.m3_monthly_evolution.insert_one({
            "evolution_id": evolution_id,
            "tenant_id": tenant_id,
            "user_id": user_id,
            "space_id": space_id,
            "month": month,
            "trajectory": trajectory,
            "new_goals": new_goals or [],
            "pillar_shifts": pillar_shifts or {},
            "source_event_id": source_event_id,
            "created_at": now,
        })

    async def append_gap_snapshot(
        self,
        tenant_id: str,
        user_id: str,
        space_id: str,
        gap_heatmap: dict[str, Any],
        pillar_deltas: dict[str, float],
        top_gaps: list[Any] | None = None,
        source_event_id: str | None = None,
    ) -> None:
        db = await self._ensure_db()
        now = datetime.now(timezone.utc)
        await db.m3_gap_snapshots.insert_one({
            "tenant_id": tenant_id,
            "user_id": user_id,
            "space_id": space_id,
            "gap_heatmap": gap_heatmap,
            "pillar_deltas": pillar_deltas,
            "top_gaps": top_gaps or [],
            "source_event_id": source_event_id,
            "created_at": now,
        })

    async def list_gap_snapshots(
        self,
        tenant_id: str,
        user_id: str,
        limit: int = 30,
    ) -> list[GapSnapshot]:
        db = await self._ensure_db()
        cursor = db.m3_gap_snapshots.find(
            {"tenant_id": tenant_id, "user_id": user_id}
        ).sort("created_at", -1).limit(limit)
        out = []
        async for doc in cursor:
            out.append(GapSnapshot(
                user_id=doc["user_id"],
                tenant_id=doc["tenant_id"],
                space_id=doc["space_id"],
                gap_heatmap=doc.get("gap_heatmap", {}),
                pillar_deltas=doc.get("pillar_deltas", {}),
                top_gaps=doc.get("top_gaps", []),
                source_event_id=doc.get("source_event_id"),
                created_at=doc.get("created_at"),
            ))
        return out

    async def get_idempotency_event_id(
        self, tenant_id: str, user_id: str, idempotency_key: str
    ) -> str | None:
        db = await self._ensure_db()
        doc = await db.m3_idempotency.find_one(
            {"tenant_id": tenant_id, "user_id": user_id, "idempotency_key": idempotency_key}
        )
        return doc.get("event_id") if doc else None

    async def record_idempotency(
        self, tenant_id: str, user_id: str, idempotency_key: str, event_id: str
    ) -> None:
        db = await self._ensure_db()
        await db.m3_idempotency.update_one(
            {"tenant_id": tenant_id, "user_id": user_id, "idempotency_key": idempotency_key},
            {"$set": {"event_id": event_id, "updated_at": datetime.now(timezone.utc)}},
            upsert=True,
        )
