from datetime import datetime, timezone
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field


class MemoryType(str, Enum):
    FACT = "fact"
    PREFERENCE = "preference"
    EVENT = "event"
    SUMMARY = "summary"
    TASK = "task"
    NOTE = "note"


class MemoryRecord(BaseModel):
    id: Optional[str] = None

    source: str
    content: str
    memory_type: MemoryType

    strength: int = 1                # דינמי
    importance: int = 3              # 1–5 (סטטי יחסית)
    confidence: float = 0.9          # 0–1 (אמינות)

    tags: List[str] = []
    parent_id: Optional[str] = None  # קשרים

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
