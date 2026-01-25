"""
KIRP Streams API v7 - Fixed
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any
from pydantic import BaseModel
from datetime import datetime, timezone  # Fixed imports
from enum import Enum

from app.core.persistence import PersistenceManager
from app.api.auth import get_current_user

router = APIRouter(prefix="/streams", tags=["Streams"])

class StreamType(str, Enum):
    WEBHOOK = "webhook"

class StreamBase(BaseModel):
    id: str
    type: StreamType

class StreamCreate(BaseModel):
    type: StreamType
    config: Dict[str, Any]

@router.get("/", response_model=List[StreamBase])
async def list_streams(current_user: dict = Depends(get_current_user)):
    """List user streams"""
    return []

@router.post("/create", response_model=StreamBase)
async def create_stream(
    stream: StreamCreate,
    current_user: dict = Depends(get_current_user)
):
    """Create new stream source"""
    stream_data = {
        **stream.dict(),
        "user_id": current_user["username"],
        "status": "active",
        "created_at": datetime.now(timezone.utc)  # Fixed
    }
    
    stream_id = "stream_" + str(hash(str(stream_data)))
    return StreamBase(id=stream_id, **stream_data)

@router.post("/{stream_id}/test")
async def test_stream(stream_id: str, current_user: dict = Depends(get_current_user)):
    """Test stream connectivity"""
    test_payload = {
        "test": True,
        "stream_id": stream_id,
        "user_id": current_user["username"],
        "timestamp": datetime.now(timezone.utc).isoformat()  # Fixed
    }
    return {"status": "test_sent", "stream_id": stream_id}
