from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class MemoryType(str, Enum):
    FACT = "fact"
    PREFERENCE = "preference"
    EVENT = "event"
    SUMMARY = "summary"
    NOTE = "note"
    MESSAGE = "message"   # chat / whatsapp / email
    TASK = "task"


class MemoryRecord(BaseModel):
    id: Optional[str] = None
    parent_id: Optional[str] = None

    source: str
    content: str
    memory_type: MemoryType

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    strength: int = 1
