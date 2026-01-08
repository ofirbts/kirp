from fastapi import APIRouter
from app.registry.agent_registry import get_versions


router = APIRouter()

@router.get("/")
def health():
    return {"status": "ok"}

@router.get("/versions")
def versions():
    return get_versions()
