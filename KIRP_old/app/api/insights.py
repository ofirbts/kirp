# app/api/insights.py
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timezone

from app.core.persistence import PersistenceManager
from app.api.auth import get_current_user

router = APIRouter(prefix="/insights", tags=["Insights"])


class InsightBase(BaseModel):
    type: str
    title: str
    description: str
    confidence: float
    impact: Optional[int] = 0


class InsightOut(InsightBase):
    id: str
    status: str
    created_at: datetime


class InsightCreate(InsightBase):
    status: str = "new"


@router.get("/", response_model=List[InsightOut])
async def list_insights():
    db = await PersistenceManager.get_db()
    docs = await db.insights.find().sort("created_at", -1).to_list(200)
    if not docs:
        now = datetime.now(timezone.utc)
        return [
            InsightOut(
                id="mock_risk_1",
                type="risk",
                title="Increased Security Concerns",
                description="The lack of recent vector data could raise security concerns regarding data integrity and access.",
                confidence=0.9,
                impact=8,
                status="new",
                created_at=now,
            )
        ]
    out: List[InsightOut] = []
    for d in docs:
        d["id"] = str(d["_id"])
        d.setdefault("status", "new")
        out.append(InsightOut(**d))
    return out


@router.get("/{user_id}")
async def get_insights(user_id: str, current_user: dict = Depends(get_current_user)):
    db = await PersistenceManager.get_db()
    insights = await db.insights.find({"user_id": user_id}).sort("created_at", -1).to_list(10)
    for i in insights:
        i["id"] = str(i.pop("_id"))
    return insights


@router.get("/summary")
async def insights_summary():
    db = await PersistenceManager.get_db()
    docs = await db.insights.find().to_list(1000)
    if not docs:
        return {"total": 0, "new": 0, "acted_on": 0, "avg_confidence": 0.0}

    total = len(docs)
    new_count = sum(1 for d in docs if d.get("status") == "new")
    acted_on = sum(1 for d in docs if d.get("status") in ("resolved", "in_progress", "acted"))
    avg_conf = sum(d.get("confidence", 0.0) for d in docs) / total
    return {
        "total": total,
        "new": new_count,
        "acted_on": acted_on,
        "avg_confidence": avg_conf,
    }


@router.post("/create", response_model=InsightOut)
async def create_insight(
    ins: InsightCreate,
    current_user: dict = Depends(get_current_user),
):
    db = await PersistenceManager.get_db()
    now = datetime.now(timezone.utc)
    payload = ins.dict()
    payload["user_id"] = current_user["username"]
    payload["created_at"] = now

    res = await db.insights.insert_one(payload)
    return InsightOut(
        id=str(res.inserted_id),
        created_at=now,
        **ins.dict(),
    )


@router.post("/{insight_id}/act")
async def mark_insight_acted(
    insight_id: str,
    current_user: dict = Depends(get_current_user),
):
    from bson import ObjectId

    db = await PersistenceManager.get_db()
    res = await db.insights.update_one(
        {"_id": ObjectId(insight_id)},
        {"$set": {"status": "acted", "acted_at": datetime.now(timezone.utc)}},
    )
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Insight not found")
    return {"status": "acted", "id": insight_id}
