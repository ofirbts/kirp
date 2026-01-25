"""
KIRP Enterprise Health API v7 - Fixed
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, List
from datetime import datetime, timezone
import os

from app.core.persistence import PersistenceManager
from app.core.redis_client import get_redis  # Fixed import

router = APIRouter(prefix="/health", tags=["Health"])

@router.get("/", response_model=Dict[str, Any])
async def system_health(current_user: dict = Depends(lambda: {"username": "system"})):
    """Enterprise system health check"""
    try:
        health = await PersistenceManager.get_system_health()
        redis = await get_redis()
        await redis.ping()
        health["redis"] = "healthy"
        return health
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))  # Fixed order

@router.get("/alerts", response_model=List[Dict[str, Any]])
async def get_alerts():
    """Active system alerts"""
    return []
