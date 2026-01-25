# app/api/sources.py
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone

from app.core.persistence import PersistenceManager
from app.api.auth import get_current_user

router = APIRouter(prefix="/sources", tags=["Sources"])


class SourceBase(BaseModel):
    name: str
    channel: str  # whatsapp / slack / email / notion / calendar / webhook
    description: Optional[str] = None
    active: bool = True
    total_items: int = 0
    last_sync: Optional[datetime] = None
    config: Dict[str, Any] = {}


class SourceOut(SourceBase):
    id: str


class SourceCreate(SourceBase):
    pass


@router.get("/", response_model=List[SourceOut])
async def list_sources(current_user: dict = Depends(get_current_user)):
    """
    מחזיר מקורות השייכים למשתמש המחובר בלבד.
    """
    db = await PersistenceManager.get_db()

    docs = await db.sources.find({"user_id": current_user["username"]}).to_list(100)

    out = []
    for d in docs:
        d["id"] = str(d["_id"])
        out.append(SourceOut(**{k: v for k, v in d.items() if k != "_id"}))

    return out


@router.post("/", response_model=SourceOut)
async def create_or_update_source(
    src: SourceCreate,
    current_user: dict = Depends(get_current_user)
):
    db = await PersistenceManager.get_db()

    payload = src.dict()
    payload["user_id"] = current_user["username"]
    payload["updated_at"] = datetime.now(timezone.utc)

    existing = await db.sources.find_one(
        {"name": src.name, "user_id": current_user["username"]}
    )

    if existing:
        await db.sources.update_one({"_id": existing["_id"]}, {"$set": payload})
        payload["id"] = str(existing["_id"])
        return SourceOut(**payload)

    payload["created_at"] = datetime.now(timezone.utc)
    res = await db.sources.insert_one(payload)
    payload["id"] = str(res.inserted_id)
    return SourceOut(**payload)
