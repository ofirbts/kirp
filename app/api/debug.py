from fastapi import APIRouter
from app.rag.vector_store import debug_info

router = APIRouter(tags=["Debug"])


@router.get("/vector-store")
def vector_store_debug():
    return debug_info()
