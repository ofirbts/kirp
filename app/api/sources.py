from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone

from app.core.persistence import PersistenceManager

router = APIRouter(tags=["Sources"])

class SourceBase(BaseModel):
    name: str
    channel: str  # whatsapp / slack / email / notion / calendar / webhook
    description: Optional[str] = None
    active: bool = True
    total_items: int = 0
    last_sync: Optional[datetime] = None
    config: Dict[str, Any] = {}


class SourceCreate(SourceBase):
    pass


class SourceOut(SourceBase):
    id: str


@router.get("/", response_model=List[SourceOut])
async def list_sources():
    """
    מחזיר את כל המקורות הרשומים.
    אם אין – אפשר להחזיר רשימת ברירת מחדל (ל־Demo).
    """
    db = await PersistenceManager.get_db()
    docs = await db.sources.find().to_list(100)

    if not docs:
        # Demo defaults – לא נשמרים אוטומטית, רק מוצגים
        defaults = [
            {
                "id": "src_whatsapp",
                "name": "WhatsApp - Team Chat",
                "channel": "whatsapp",
                "description": "Team operational chat",
                "active": True,
                "total_items": 245,
                "last_sync": datetime(2026, 1, 15, tzinfo=timezone.utc),
                "config": {},
            },
            {
                "id": "src_notion",
                "name": "Notion Knowledge Base",
                "channel": "notion",
                "description": "Product & technical docs",
                "active": True,
                "total_items": 78,
                "last_sync": datetime(2026, 1, 15, tzinfo=timezone.utc),
                "config": {},
            },
            {
                "id": "src_slack",
                "name": "Slack - Engineering",
                "channel": "slack",
                "description": "Engineering discussions",
                "active": True,
                "total_items": 189,
                "last_sync": datetime(2026, 1, 15, tzinfo=timezone.utc),
                "config": {},
            },
            {
                "id": "src_email",
                "name": "Support Emails",
                "channel": "email",
                "description": "Customer support inbox",
                "active": True,
                "total_items": 523,
                "last_sync": datetime(2026, 1, 15, tzinfo=timezone.utc),
                "config": {},
            },
        ]
        return [SourceOut(**d) for d in defaults]

    out = []
    for d in docs:
        d["id"] = str(d["_id"])
        out.append(SourceOut(**{k: v for k, v in d.items() if k != "_id"}))
    return out


@router.post("/", response_model=SourceOut)
async def create_or_update_source(src: SourceCreate):
    """
    יצירת / עדכון מקור חדש.
    """
    db = await PersistenceManager.get_db()
    existing = await db.sources.find_one({"name": src.name})

    payload = src.dict()
    payload["updated_at"] = datetime.now(timezone.utc)

    if existing:
        await db.sources.update_one({"_id": existing["_id"]}, {"$set": payload})
        existing.update(payload)
        existing["id"] = str(existing["_id"])
        return SourceOut(**{k: v for k, v in existing.items() if k != "_id"})
    else:
        payload["created_at"] = datetime.now(timezone.utc)
        res = await db.sources.insert_one(payload)
        payload["id"] = str(res.inserted_id)
        return SourceOut(**payload)
