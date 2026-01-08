from fastapi import APIRouter
from app.rag.vector_store import debug_info

router = APIRouter(tags=["Status"])

@router.get("/")
async def system_status():
    vector = debug_info()
    return {
        "api": "live",
        "ui": "live", 
        "bot": "live",
        "memories_loaded": vector.get("vectors_count_ram", 0),
        "tasks_count": 0, 
        "vector_store": vector
    }
