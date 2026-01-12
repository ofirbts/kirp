from fastapi import APIRouter
from app.storage.tasks import tasks_collection
from app.services.export.notion import export_task_to_notion

router = APIRouter(prefix="/export", tags=["export"])

@router.post("/notion")
async def export_to_notion():
    tasks = await tasks_collection.find().to_list(50)
    for task in tasks:
        await export_task_to_notion(task)
