from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum

class JobStatus(str, Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class Job(BaseModel):
    id: Optional[str] = None
    status: JobStatus = JobStatus.PENDING
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    result: Optional[dict] = None
