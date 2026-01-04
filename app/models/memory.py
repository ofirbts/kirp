from enum import Enum
from datetime import datetime
from pydantic import BaseModel


class MemoryType(str, Enum):
    FACT = "fact"
    PREFERENCE = "preference"
    EVENT = "event"
    NOTE = "note"


class MemoryRecord(BaseModel):
    source: str
    content: str
    memory_type: MemoryType
    created_at: datetime = datetime.utcnow()
