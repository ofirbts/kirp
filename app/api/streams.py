from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime, timezone

from app.core.persistence import PersistenceManager

router = APIRouter(prefix="/streams", tags=["streams"])


class StreamCreate(BaseModel):
    type: str  # whatsapp_webhook / slack_events / custom_webhook
    endpoint: str
    config: Dict[str, Any] = {}


@router.post("/register")
async def register_stream(stream: StreamCreate):
    db = await PersistenceManager.get_db()
    now = datetime.now(timezone.utc)
    payload = {
        "type": stream.type,
        "endpoint": stream.endpoint,
        "config": stream.config,
        "active": True,
        "created_at": now,
        "updated_at": now,
    }
    await db.streams.insert_one(payload)
    await PersistenceManager.save_event("stream_registered", {
        "type": stream.type,
        "endpoint": stream.endpoint,
    })
    return {"status": "registered"}
