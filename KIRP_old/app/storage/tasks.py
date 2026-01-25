# app/storage/tasks.py
from typing import List
from app.models.task import Task

# זמני – אחסון בזיכרון
_TASKS: List[Task] = []

async def create_task(task: Task):
    _TASKS.append(task)
    return task

async def fetch_open_tasks() -> List[Task]:
    return _TASKS
