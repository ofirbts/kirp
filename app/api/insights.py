# app/api/insights.py
from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timezone

from app.core.persistence import PersistenceManager

router = APIRouter(prefix="/insights", tags=["Insights"])

class InsightOut(BaseModel):
    id: str
    type: str  # trend / opportunity / risk
    title: str
    description: str
    confidence: float
    impact: int
    status: str  # new / in_progress / resolved
    created_at: datetime

@router.get("/", response_model=List[InsightOut])
async def list_insights():
    db = await PersistenceManager.get_db()
    docs = await db.insights.find().sort("created_at", -1).to_list(200)
    if not docs:
        # fallback – mockים חכמים, כמו שאתה רואה בדשבורד
        now = datetime.now(timezone.utc)
        defaults = [
            InsightOut(
                id="mock_risk_1",
                type="risk",
                title="Increased Security Concerns",
                description="The lack of recent vector data could raise security concerns regarding data integrity and access.",
                confidence=0.9,
                impact=8,
                status="new",
                created_at=now,
            ),
            InsightOut(
                id="mock_trend_1",
                type="trend",
                title="User Interest in Data-Driven Insights",
                description="The absence of recent data may reflect a shift in user interest towards more data-driven insights.",
                confidence=0.9,
                impact=7,
                status="new",
                created_at=now,
            ),
            InsightOut(
                id="mock_opportunity_1",
                type="opportunity",
                title="Improvement in Data Monitoring Systems",
                description="The lack of recent data indicates a need for improved monitoring systems.",
                confidence=0.9,
                impact=8,
                status="new",
                created_at=now,
            ),
        ]
        return defaults

    out: List[InsightOut] = []
    for d in docs:
        d["id"] = str(d["_id"])
        del d["_id"]
        out.append(InsightOut(**d))
    return out
