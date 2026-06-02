"""
Domain store — MongoDB collections for decisions, signals, content_intelligence, visuals.

Uses same Mongo DB as EventStore. Tenant-scoped; no direct mutations without events
for audit trail; these collections are read/write for UI and derived data.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

logger = logging.getLogger(__name__)

_store: Any = None


async def _get_db():
    global _store
    if _store is None:
        from motor.motor_asyncio import AsyncIOMotorClient
        uri = os.getenv(
            "MONGO_URI",
            "mongodb://root:example@mongodb:27017/kirp?authSource=admin"
        )
        client = AsyncIOMotorClient(uri)

        db = client.get_default_database()
        if db is None:
            db = client["kirp"]

        await db.command("ping")

        _store = db
        logger.info("DomainStore connected to MongoDB")

    return _store



async def list_decisions(
    tenant_id: str,
    space_id: str | None = None,
    agent_id: str | None = None,
    limit: int = 100,
    since: datetime | None = None,
) -> list[dict[str, Any]]:
    db = await _get_db()
    q: dict[str, Any] = {"tenant_id": tenant_id}
    if space_id:
        q["space_id"] = space_id
    if agent_id:
        q["agent_id"] = agent_id
    if since:
        q["created_at"] = {"$gte": since}
    cursor = db.decisions.find(q).sort("created_at", -1).limit(limit)
    docs = await cursor.to_list(length=limit)
    return [_doc_to_decision(d) for d in docs]


async def get_decision(decision_id: str, tenant_id: str) -> dict[str, Any] | None:
    db = await _get_db()
    doc = await db.decisions.find_one({"_id": decision_id, "tenant_id": tenant_id})
    return _doc_to_decision(doc) if doc else None


async def create_decision(
    tenant_id: str,
    space_id: str,
    agent_id: str,
    output: dict[str, Any],
    confidence: float = 0.9,
    status: str = "completed",
    inputs: list[dict] | None = None,
    trace: list[dict] | None = None,
    workflow_id: str | None = None,
) -> str:
    db = await _get_db()
    did = str(uuid4())
    now = datetime.now(timezone.utc)
    doc = {
        "_id": did,
        "tenant_id": tenant_id,
        "space_id": space_id,
        "agent_id": agent_id,
        "workflow_id": workflow_id,
        "inputs": inputs or [],
        "trace": trace or [],
        "output": output,
        "confidence": confidence,
        "status": status,
        "error_message": None,
        "created_at": now,
    }
    await db.decisions.insert_one(doc)
    return did


def _doc_to_decision(doc: dict) -> dict[str, Any]:
    created = doc.get("created_at")
    if hasattr(created, "isoformat"):
        created = created.isoformat().replace("+00:00", "Z")
    return {
        "id": doc["_id"],
        "createdAt": created,
        "tenantId": doc["tenant_id"],
        "spaceId": doc.get("space_id"),
        "agentId": doc["agent_id"],
        "workflowId": doc.get("workflow_id"),
        "inputs": doc.get("inputs", []),
        "trace": doc.get("trace", []),
        "output": doc.get("output", {}),
        "confidence": doc.get("confidence", 0),
        "status": doc.get("status", "completed"),
        "errorMessage": doc.get("error_message"),
    }


# ---------- Signals ----------


async def list_signals(
    tenant_id: str,
    space_id: str | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    db = await _get_db()
    q: dict[str, Any] = {"tenant_id": tenant_id}
    if space_id:
        q["space_id"] = space_id
    cursor = db.signals.find(q).sort("timestamp", -1).limit(limit)
    docs = await cursor.to_list(length=limit)
    return [_doc_to_signal(d) for d in docs]


async def upsert_signal(
    tenant_id: str,
    space_id: str,
    topic: str,
    relevance: int,
    urgency: str,
    trend: str,
    source: str = "api",
) -> str:
    db = await _get_db()
    now = datetime.now(timezone.utc)
    doc = {
        "tenant_id": tenant_id,
        "space_id": space_id,
        "topic": topic,
        "relevance": relevance,
        "urgency": urgency,
        "trend": trend,
        "source": source,
        "timestamp": now,
    }
    sid = f"{tenant_id}:{topic}"
    await db.signals.update_one(
        {"_id": sid},
        {"$set": {**doc, "_id": sid}},
        upsert=True,
    )
    return sid


def _doc_to_signal(doc: dict) -> dict[str, Any]:
    ts = doc.get("timestamp")
    if hasattr(ts, "isoformat"):
        ts = ts.isoformat().replace("+00:00", "Z")
    return {
        "id": doc.get("_id", ""),
        "topic": doc.get("topic", ""),
        "relevance": doc.get("relevance", 0),
        "urgency": doc.get("urgency", "medium"),
        "trend": doc.get("trend", "stable"),
        "source": doc.get("source", "api"),
        "timestamp": ts,
    }


# ---------- Content intelligence ----------


async def list_content_intelligence(
    tenant_id: str,
    space_id: str | None = None,
    limit: int = 100,
    since: datetime | None = None,
) -> list[dict[str, Any]]:
    db = await _get_db()
    q: dict[str, Any] = {"tenant_id": tenant_id}
    if space_id:
        q["space_id"] = space_id
    if since:
        q["published_at"] = {"$gte": since}
    cursor = db.content_intelligence.find(q).sort("published_at", -1).limit(limit)
    docs = await cursor.to_list(length=limit)
    return [_doc_to_content(d) for d in docs]


async def create_content_intelligence(
    tenant_id: str,
    space_id: str,
    trace_id: str,
    topic_hint: str,
    platform: str,
    status: str = "draft",
    content_preview: str | None = None,
) -> str:
    db = await _get_db()
    cid = str(uuid4())
    now = datetime.now(timezone.utc)
    doc = {
        "_id": cid,
        "tenant_id": tenant_id,
        "space_id": space_id,
        "trace_id": trace_id,
        "topic_hint": topic_hint,
        "platform": platform,
        "status": status,
        "content_preview": content_preview or "",
        "published_at": now,
    }
    await db.content_intelligence.insert_one(doc)
    return cid


def _doc_to_content(doc: dict) -> dict[str, Any]:
    pub = doc.get("published_at")
    if hasattr(pub, "isoformat"):
        pub = pub.isoformat().replace("+00:00", "Z")
    return {
        "id": doc["_id"],
        "trace_id": doc.get("trace_id"),
        "topic_hint": doc.get("topic_hint", ""),
        "platform": doc.get("platform", ""),
        "status": doc.get("status", "draft"),
        "published_at": pub,
        "content_preview": doc.get("content_preview", ""),
    }


# ---------- Visuals ----------


async def list_visuals(
    tenant_id: str,
    space_id: str | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    db = await _get_db()
    q: dict[str, Any] = {"tenant_id": tenant_id}
    if space_id:
        q["space_id"] = space_id
    cursor = db.visuals.find(q).sort("created_at", -1).limit(limit)
    docs = await cursor.to_list(length=limit)
    return [_doc_to_visual(d) for d in docs]


async def create_visual(
    tenant_id: str,
    space_id: str,
    name: str,
    chart_type: str = "bar",
    config: dict[str, Any] | None = None,
) -> str:
    db = await _get_db()
    vid = str(uuid4())
    now = datetime.now(timezone.utc)
    doc = {
        "_id": vid,
        "tenant_id": tenant_id,
        "space_id": space_id,
        "name": name,
        "chart_type": chart_type,
        "config": config or {},
        "created_at": now,
    }
    await db.visuals.insert_one(doc)
    return vid


def _doc_to_visual(doc: dict) -> dict[str, Any]:
    created = doc.get("created_at")
    if hasattr(created, "isoformat"):
        created = created.isoformat().replace("+00:00", "Z")
    return {
        "id": doc["_id"],
        "tenantId": doc["tenant_id"],
        "spaceId": doc.get("space_id"),
        "name": doc.get("name", ""),
        "chartType": doc.get("chart_type", "bar"),
        "config": doc.get("config", {}),
        "createdAt": created,
    }
