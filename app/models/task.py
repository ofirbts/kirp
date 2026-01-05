from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone

class Task(BaseModel):
    id: Optional[str] = None
    title: str
    source_memory_id: Optional[str]
    completed: bool = False
    created_at: datetime = datetime.now(timezone.utc)
