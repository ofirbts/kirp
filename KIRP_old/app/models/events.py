from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
import uuid

class KIRPEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    trace_id: str  # מזהה שמלווה את כל שרשרת הפעולות
    event_type: str # e.g., "data_ingested", "insight_generated", "agent_action"
    source: str     # מי יצר את האירוע (UI, API, Engine)
    payload: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        frozen = True # אירוע הוא Immutable