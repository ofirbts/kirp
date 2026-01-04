from fastapi import APIRouter
from typing import List
from app.models.ingest import IngestRequest
from app.services.pipeline import ingest_text

router = APIRouter()


@router.post("/batch")
async def ingest_batch(items: List[IngestRequest]):
    for item in items:
        await ingest_text(item.content, source=item.source)
    return {"status": "ok", "count": len(items)}
