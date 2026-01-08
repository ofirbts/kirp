# app/api/debug.py
from fastapi import APIRouter, HTTPException
from app.core.persistence import PersistenceManager
from app.agent.agent import agent

router = APIRouter(tags=["debug"])


@router.get("/sessions")
def list_sessions():
    return PersistenceManager.list_sessions()


@router.get("/metrics")
def metrics():
    return agent.metrics.snapshot()


@router.get("/sessions/{session_id}")
def get_session(session_id: str):
    session = PersistenceManager.load_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.get("/agent/state")
def get_agent_state():
    return agent.dump_state()


@router.post("/agent/reset")
def reset_agent():
    agent.reset()
    return {"status": "agent reset"}


@router.get("/events")
def get_events(limit: int = 100):
    return PersistenceManager.read_events(limit)


@router.get("/observability")
def observability():
    return {
        "qps": agent.observability.qps(),
        "drift": agent.observability.drift(),
    }
