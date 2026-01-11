from fastapi import APIRouter
from app.agent.agent import agent
from app.core.persistence import PersistenceManager

router = APIRouter()

@router.get("/state")
def debug_state():
    return agent.dump_state()


@router.get("/memories")
def debug_memories():
    snapshot = agent.memory_hub.snapshot(limit=50)
    return {
        "memories": snapshot["recent_memories"],
        "stats": snapshot["stats"],
        "total_vectors": snapshot["total_vectors"],
    }


@router.get("/events")
def debug_events(limit: int = 50):
    return PersistenceManager.read_events(limit=limit)

@router.get("/timeline")
def debug_timeline(limit: int = 50):
    return PersistenceManager.read_events(limit=limit)
