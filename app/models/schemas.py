from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Literal
from datetime import datetime, timezone, timezone

class KnowledgeItem(BaseModel):
    id: str
    source: str              # "whatsapp", "notion", "email"
    category: Literal["technical", "business", "support", "general"]
    title: str
    text: str
    confidence: float = 0.0
    created_at: datetime = Field(default_factory=datetime.now(timezone.utc))
    metadata: Dict[str, Any] = {}
    embedding_id: Optional[str] = None

class Insight(BaseModel):
    id: str
    type: Literal["trend", "opportunity", "risk"]
    title: str
    description: str
    confidence: float
    status: Literal["new", "in_progress", "resolved"] = "new"
    impact_score: Optional[int] = None
    created_at: datetime = Field(default_factory=datetime.now(timezone.utc))

class IngestionJob(BaseModel):
    id: str
    source: str
    status: Literal["PENDING", "CHUNKED", "EMBEDDED", "DONE", "FAILED"]
    chunks_count: int = 0
    processing_time_ms: Optional[int] = None
    error_message: Optional[str] = None
    updated_at: datetime = Field(default_factory=datetime.utcnow)