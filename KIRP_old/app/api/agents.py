# app/api/agents.py
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timezone

from app.core.persistence import PersistenceManager
from app.api.auth import get_current_user

router = APIRouter(prefix="/agents", tags=["Agents"])


class AgentOut(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    created_at: datetime


class AgentRunRequest(BaseModel):
    task: str
    user_id: str


@router.get("/", response_model=List[AgentOut])
async def list_agents():
    db = await PersistenceManager.get_db()
    docs = await db.agents.find().to_list(100)
    out = []
    for d in docs:
        out.append(
            AgentOut(
                id=str(d["_id"]),
                name=d.get("name", "Unnamed Agent"),
                description=d.get("description"),
                created_at=d.get("created_at", datetime.now(timezone.utc)),
            )
        )
    return out


@router.post("/{agent_id}/run")
async def run_agent(
    agent_id: str,
    payload: AgentRunRequest,
    current_user: dict = Depends(get_current_user),
):
    # סטאב – אפשר לחבר אחר כך ל־AgentEngine
    return {
        "status": "ok",
        "agent_id": agent_id,
        "task": payload.task,
        "user_id": payload.user_id,
        "started_at": datetime.now(timezone.utc).isoformat(),
    }


@router.delete("/{agent_id}/delete")
async def delete_agent(
    agent_id: str,
    current_user: dict = Depends(get_current_user),
):
    from bson import ObjectId

    db = await PersistenceManager.get_db()
    res = await db.agents.delete_one({"_id": ObjectId(agent_id)})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Agent not found")
    return {"status": "deleted", "id": agent_id}
