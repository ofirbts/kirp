from pydantic import BaseModel
from datetime import datetime, timezone

class IngestRequest(BaseModel):
    source: str
    content: str
    timestamp: datetime
