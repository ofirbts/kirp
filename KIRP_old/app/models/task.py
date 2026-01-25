# app/models/task.py
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, timezone


class Task(BaseModel):
    id: Optional[str] = None
    title: str
    source_memory_id: Optional[str] = None
    completed: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
