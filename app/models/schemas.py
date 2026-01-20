from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field, EmailStr
from datetime import datetime, timezone

class KnowledgeItem(BaseModel):
    id: str
    source: str              # "whatsapp", "notion", "email"
    category: Literal["technical", "business", "support", "general"]
    title: str
    text: str
    confidence: float = 0.0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
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
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class Action(BaseModel):
    id: str
    description: str
    agent_id: str  # איזה סוכן יכול לבצע את זה
    status: Literal["pending", "executed", "failed"] = "pending"

class IngestionJob(BaseModel):
    id: str
    source: str
    status: Literal["PENDING", "CHUNKED", "EMBEDDED", "DONE", "FAILED"]
    chunks_count: int = 0
    processing_time_ms: Optional[int] = None
    error_message: Optional[str] = None
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    recommended_actions: List[Action] = []

class SystemConfig(BaseModel):
    """הגדרות ליבת המערכת שניתנות לשינוי בזמן אמת"""
    llm_model: str = "gpt-4-turbo"
    chunk_size: int = 500
    chunk_overlap: int = 50
    rag_threshold: float = 0.7  # סף ביטחון מינימלי להחזרת תשובה
    active_learning: bool = True

class TechnicalImprovement(BaseModel):
    """הצעה לשיפור טכני שהופקה מהלוגים"""
    id: str
    target_config_key: str  # למשל "chunk_size"
    new_value: Any          # למשל 800
    reasoning: str          # למה ה-AI חושב שזה כדאי
    impact_level: Literal["low", "medium", "high"]
    applied: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class User(BaseModel):
    email: EmailStr  # שימוש ב-EmailStr במקום Alias מסורבל
    full_name: str
    avatar_url: Optional[str] = None
    role: str = "user"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_login: Optional[datetime] = None

class TokenData(BaseModel):
    email: Optional[str] = None