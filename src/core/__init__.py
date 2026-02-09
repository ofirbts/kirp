"""
Core Intelligence Engine.

- Event store (MongoDB)
- RAG engine (Qdrant + hybrid search)
- Agent framework (registry, triggers, autonomy)
- Schema engine (tasks, projects, life areas)
- Governance (OPA, approvals, audit)
"""

from src.core.event_store import Event, EventStore
from src.core.event_registry import EventRegistry, get_event_registry
from src.core.rag_engine import RAGEngine, RAGResponse, RetrievalResult
from src.core.agent_framework import AgentFramework, AgentSpec, AutonomyLevel
from src.core.schema_engine import SchemaEngine, SchemaEntity, SchemaNode
from src.core.governance import GovernanceEngine, GovernanceCheck, ApprovalStatus

__all__ = [
    "Event",
    "EventStore",
    "EventRegistry",
    "get_event_registry",
    "RAGEngine",
    "RAGResponse",
    "RetrievalResult",
    "AgentFramework",
    "AgentSpec",
    "AutonomyLevel",
    "SchemaEngine",
    "SchemaEntity",
    "SchemaNode",
    "GovernanceEngine",
    "GovernanceCheck",
    "ApprovalStatus",
]
