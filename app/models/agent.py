from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class AgentCreate(BaseModel):
    name: str
    type: str
    description: str
    capabilities: List[str] = []
    autonomous: bool = True
    schedule: Optional[str] = None


class AgentModel(AgentCreate):
    id: str
    actions_count: int = 0
    success_rate: float = 0.0
    last_run: Optional[datetime] = None
    status: str = "active"
