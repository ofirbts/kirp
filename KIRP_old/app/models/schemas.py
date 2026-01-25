"""
KIRP OS v7 - Production Pydantic Schemas
Complete data layer for all entities
"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum

# === CORE ENTITIES ===
class MemoryType(str, Enum):
    TASK = "task"
    EVENT = "event"
    KNOWLEDGE = "knowledge"
    PREFERENCE = "preference"

class UserRole(str, Enum):
    ADMIN = "admin"
    USER = "user"

class JobStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class IngestRequest(BaseModel):
    text: str = Field(..., max_length=10000)
    metadata: Dict[str, Any] = {}
    source: str = "api"

class QueryRequest(BaseModel):
    query: str = Field(..., max_length=5000)
    context_query: Optional[str] = None
    k: int = Field(default=6, ge=1, le=20)

class AgentResponse(BaseModel):
    content: str
    intent: str
    effects: List[str]
    confidence: float
    tokens_used: Optional[Dict[str, int]] = None

# === USERS & AUTH ===
class UserCreate(BaseModel):
    username: str = Field(..., min_length=3)
    password: str = Field(..., min_length=8)
    full_name: str
    phone: Optional[str] = None

class UserOut(BaseModel):
    user_id: str
    full_name: str
    role: UserRole
    created_at: datetime

# === JOBS & TASKS ===
class JobCreate(BaseModel):
    source: str
    task: str
    priority: str = "normal"

class JobStatusResponse(BaseModel):
    id: str
    status: JobStatus
    progress: float
    created_at: datetime

# === EVENTS & TRACES ===
class EventPayload(BaseModel):
    event_type: str
    data: Dict[str, Any]
    user_id: str
    trace_id: str

# === API RESPONSES ===
class HealthResponse(BaseModel):
    status: str
    uptime_seconds: float
    services: Dict[str, Dict[str, Any]]
    metrics: Dict[str, Any]

class DashboardResponse(BaseModel):
    knowledge_items: int
    active_jobs: int
    new_insights: int
    health_status: str
