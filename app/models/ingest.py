from pydantic import BaseModel
from datetime import datetime

class IngestRequest(BaseModel):
    source: str
    content: str
    timestamp: datetime
