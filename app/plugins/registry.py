from fastapi import APIRouter
from app.core.persistence import PersistenceManager

router = APIRouter(prefix="/registry", tags=["Registry"])

@router.get("/sources")
async def get_all_sources():
    sources = await PersistenceManager.get_sources() # השתמש במתודה שכתבנו קודם
    return {"status": "success", "data": sources}

@router.get("/agents")
async def get_agents_status():
    agents = await PersistenceManager.get_agents_stats()
    return {"status": "success", "data": agents}