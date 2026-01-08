from pydantic import BaseModel, Field
from typing import List, Dict, Any
from datetime import datetime
import uuid

class TraceEvent(BaseModel):
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    type: str
    payload: Dict[str, Any]

class Trace(BaseModel):
    trace_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    question: str
    events: List[TraceEvent] = []
