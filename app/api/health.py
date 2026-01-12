from fastapi import APIRouter

router = APIRouter()

@router.get("")
async def health_check():
    return {"status": "ok", "service": "kirp-os"}

@router.get("/versions")
async def get_versions():
    return {"version": "1.0.0", "engine": "gemini-flash-3"}
