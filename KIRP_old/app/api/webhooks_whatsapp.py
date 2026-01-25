"""
KIRP WhatsApp Webhooks v7 - FIXED
"""
import os
import uuid
import json
import logging
from typing import Dict, Any
from fastapi import APIRouter, Request, HTTPException, Query, Depends
from datetime import datetime, timezone

from app.core.persistence import PersistenceManager
from app.agent.agent import get_agent

router = APIRouter(prefix="/webhooks/whatsapp", tags=["WhatsApp"])
logger = logging.getLogger(__name__)

VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "kirp-secure-2026")

@router.get("/")
async def verify_webhook(
    mode: str = Query(...),
    token: str = Query(...), 
    challenge: str = Query(...)
):
    """WhatsApp webhook verification - FIXED ORDER"""
    if mode == "subscribe" and token == VERIFY_TOKEN:
        return challenge
    raise HTTPException(status_code=403, detail="Verification failed")  # ✅ FIXED

@router.post("/")
async def receive_whatsapp(request: Request):
    """Production WhatsApp message handler"""
    try:
        body = await request.json()
        sender = body.get("from", "unknown")
        text = body.get("text", "")
        
        if not text:
            return {"status": "ok"}
        
        user_id = f"whatsapp_{sender[:8]}"
        agent = get_agent(user_id=user_id)
        response = await agent.process_task(text[:500])
        
        logger.info(f"✅ WhatsApp [{sender}]: {text[:30]}")
        return {"status": "processed"}
    except Exception as e:
        logger.error(f"❌ WhatsApp webhook error: {e}")
        return {"status": "error"}
