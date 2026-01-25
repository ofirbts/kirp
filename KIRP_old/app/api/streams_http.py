# app/api/streams_http.py
from fastapi import APIRouter
from pydantic import BaseModel
from typing import List

router = APIRouter(prefix="/streams", tags=["Streams"])


class StreamCreate(BaseModel):
    name: str
    source: str


class StreamOut(StreamCreate):
    id: str
    status: str = "active"


_FAKE_STREAMS: dict[str, StreamOut] = {}


@router.post("/register", response_model=StreamOut)
async def register_stream(stream: StreamCreate):
    # סטאב בזיכרון – מספיק כדי שה־UI יעבוד
    sid = f"stream_{len(_FAKE_STREAMS) + 1}"
    obj = StreamOut(id=sid, **stream.dict())
    _FAKE_STREAMS[sid] = obj
    return obj


@router.get("/list", response_model=List[StreamOut])
async def list_streams():
    return list(_FAKE_STREAMS.values())


@router.delete("/delete/{stream_id}")
async def delete_stream(stream_id: str):
    _FAKE_STREAMS.pop(stream_id, None)
    return {"status": "deleted", "id": stream_id}
