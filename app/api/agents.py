# app/api/agents.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Any, Dict
from datetime import datetime, timezone

from app.core.persistence import PersistenceManager
from app.agent.agent import agent as omni_agent  # OmniAgent הגלובלי

router = APIRouter(prefix="/agents", tags=["agents"])

class AgentOut(BaseModel):
    id: str
    name: str
    type: str
    description: str
    autonomous: bool = True
    actions_count: int = 0
    success_rate: float = 0.0
    last_run: Optional[datetime] = None
    status: str = "active"

class AgentCreate(BaseModel):
    name: str
    type: str
    description: str
    capabilities: List[str] = []
    autonomous: bool = True
    schedule: Optional[str] = None

class AgentRunRequest(BaseModel):
    task: str
    user_id: str = "ofir"
    context_query: Optional[str] = None

class AgentRunResponse(BaseModel):
    agent_id: str
    result: str
    executed_at: datetime

@router.get("/", response_model=List[AgentOut])
async def list_agents():
    db = await PersistenceManager.get_db()
    docs = await db.agents.find().to_list(50)
    if not docs:
        defaults = [
            AgentOut(
                id="agent_creator",
                name="Agent Creator",
                type="custom",
                description="סוכן מטא שיוצר סוכנים חכמים חדשים על בסיס דרישות המשתמש.",
                autonomous=True,
                actions_count=34,
                success_rate=0.97,
                last_run=datetime(2026, 1, 16, 10, 0, tzinfo=timezone.utc),
                status="active",
            ),
            AgentOut(
                id="problem_detector",
                name="Problem Detector",
                type="problem_solver",
                description="מזהה בעיות פוטנציאליות ומציע פתרונות.",
                autonomous=True,
                actions_count=423,
                success_rate=0.88,
                last_run=datetime(2026, 1, 15, 10, 15, tzinfo=timezone.utc),
                status="active",
            ),
            AgentOut(
                id="auto_summarizer",
                name="Auto Summarizer",
                type="content_creator",
                description="יוצר סיכומים אוטומטיים של תוכן חדש.",
                autonomous=True,
                actions_count=856,
                success_rate=0.91,
                last_run=datetime(2026, 1, 15, 11, 30, tzinfo=timezone.utc),
                status="active",
            ),
            AgentOut(
                id="content_analyzer",
                name="Content Analyzer",
                type="analyzer",
                description="מנתח תוכן ומזהה דפוסים, טרנדים וישויות.",
                autonomous=True,
                actions_count=1247,
                success_rate=0.94,
                last_run=datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc),
                status="active",
            ),
        ]
        return defaults

    out: List[AgentOut] = []
    for d in docs:
        d["id"] = str(d["_id"])
        out.append(AgentOut(**{k: v for k, v in d.items() if k != "_id"}))
    return out

@router.post("/create", response_model=AgentOut)
async def create_agent(agent: AgentCreate):
    db = await PersistenceManager.get_db()
    now = datetime.now(timezone.utc)
    payload: Dict[str, Any] = {
        "name": agent.name,
        "type": agent.type,
        "description": agent.description,
        "capabilities": agent.capabilities,
        "autonomous": agent.autonomous,
        "schedule": agent.schedule,
        "actions_count": 0,
        "success_rate": 0.0,
        "status": "active",
        "created_at": now,
        "updated_at": now,
    }
    res = await db.agents.insert_one(payload)
    payload["id"] = str(res.inserted_id)
    return AgentOut(**payload)

@router.get("/{agent_id}", response_model=AgentOut)
async def get_agent(agent_id: str):
    db = await PersistenceManager.get_db()
    doc = await db.agents.find_one({"_id": agent_id})  # אם אתה שומר ObjectId – תעדכן
    if not doc:
        # אפשר גם לחפש ב־defaults אם תרצה
        raise HTTPException(status_code=404, detail="Agent not found")
    doc["id"] = str(doc["_id"])
    del doc["_id"]
    return AgentOut(**doc)

@router.post("/{agent_id}/run", response_model=AgentRunResponse)
async def run_agent(agent_id: str, req: AgentRunRequest):
    """
    מריץ את ה־OmniAgent על משימה, עם user_id ו־context_query.
    כרגע agent_id לא משנה את ה־role, אבל אפשר להרחיב.
    """
    executed_at = datetime.now(timezone.utc)
    result = await omni_agent.process_task(
        task_description=req.task,
        user_id=req.user_id,
        context_query=req.context_query,
    )
    return AgentRunResponse(
        agent_id=agent_id,
        result=result,
        executed_at=executed_at,
    )
