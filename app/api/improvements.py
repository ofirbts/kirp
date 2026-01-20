# app/api/improvements.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Any
from datetime import datetime, timezone
from bson import ObjectId

from app.core.persistence import PersistenceManager

router = APIRouter(prefix="/improvements", tags=["improvements"])


class ImprovementOut(BaseModel):
    id: str
    target_config_key: str
    new_value: Any
    reasoning: str
    impact_level: str
    applied: bool
    created_at: datetime
    applied_at: datetime | None = None


@router.get("/pending", response_model=List[ImprovementOut])
async def get_pending_improvements():
    pending = await PersistenceManager.get_pending_improvements()
    out: List[ImprovementOut] = []
    for imp in pending:
        imp["id"] = str(imp["_id"])
        del imp["_id"]
        out.append(ImprovementOut(**imp))
    return out


@router.get("/", response_model=List[ImprovementOut])
async def list_all_improvements():
    db = await PersistenceManager.get_db()
    docs = await db.improvements.find().sort("created_at", -1).to_list(200)
    out: List[ImprovementOut] = []
    for imp in docs:
        imp["id"] = str(imp["_id"])
        del imp["_id"]
        out.append(ImprovementOut(**imp))
    return out


@router.get("/{imp_id}", response_model=ImprovementOut)
async def get_improvement(imp_id: str):
    db = await PersistenceManager.get_db()
    try:
        oid = ObjectId(imp_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid improvement id")

    imp = await db.improvements.find_one({"_id": oid})
    if not imp:
        raise HTTPException(status_code=404, detail="Improvement not found")

    imp["id"] = str(imp["_id"])
    del imp["_id"]
    return ImprovementOut(**imp)


@router.post("/{imp_id}/apply")
async def apply_improvement(imp_id: str):
    await PersistenceManager.apply_config_change(imp_id)
    return {"status": "applied", "id": imp_id}


@router.post("/{imp_id}/dismiss")
async def dismiss_improvement(imp_id: str):
    db = await PersistenceManager.get_db()
    try:
        oid = ObjectId(imp_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid improvement id")

    res = await db.improvements.update_one(
        {"_id": oid},
        {"$set": {"dismissed": True, "dismissed_at": datetime.now(timezone.utc)}},
    )
    if not res.matched_count:
        raise HTTPException(status_code=404, detail="Improvement not found")

    return {"status": "dismissed", "id": imp_id}
