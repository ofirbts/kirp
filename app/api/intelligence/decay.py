from fastapi import APIRouter
from app.services.memory_intelligence.strength import decay_memory_strength

router = APIRouter(prefix="/intelligence", tags=["intelligence"])


@router.post("/decay")
async def decay():
    await decay_memory_strength()
    return {"status": "decay completed"}
