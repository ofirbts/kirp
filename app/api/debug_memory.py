# app/api/debug_memory.py

from fastapi import APIRouter
from app.agent.agent import agent

router = APIRouter(tags=["Debug"])

@router.get("/debug/memory")
def debug_memory():
    return agent.memory.snapshot()
