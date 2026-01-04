from fastapi import APIRouter
from app.storage.tasks import fetch_open_tasks

router = APIRouter(prefix="/tasks", tags=["Tasks"])

@router.get("/")
async def list_tasks():
    return await fetch_open_tasks()
