from fastapi import APIRouter
from app.core.versions import VERSIONS

router = APIRouter()

@router.get("/")
def health():
    return {"status": "ok"}

@router.get("/versions")
def versions():
    return VERSIONS
