# app/api/dashboard.py
from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timezone
from typing import Dict, Any

from app.core.persistence import PersistenceManager
from app.api.auth import get_current_user

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/summary/{user_id}")
async def dashboard_summary(
    user_id: str,
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:

    # אבטחה: מניעת גישה לדשבורד של משתמש אחר
    if current_user.get("username") != user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    try:
        # מטריקות אמיתיות מה־DB
        metrics = await PersistenceManager.get_dashboard_metrics(user_id)

        # סטטוס מערכת
        health_status = await PersistenceManager.get_system_health()

        return {
            "metrics": metrics,
            "health": health_status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    except Exception:
        raise HTTPException(status_code=500, detail="Dashboard error")
