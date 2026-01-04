from enum import Enum
from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class MemoryType(str, Enum):
    FACT = "fact"
    PREFERENCE = "preference"
    EVENT = "event"
    MESSAGE = "message"


class MemoryRecord(BaseModel):
    content: str
    memory_type: MemoryType = MemoryType.MESSAGE
    source: str = "unknown"
    created_at: datetime = datetime.utcnow()
    metadata: Optional[dict] = None
