# app/api/webhooks/whatsapp.py
"""
KIRP WhatsApp Webhooks - Unified Production Version
"""
import os
import uuid
import json
import logging
import redis
from fastapi import APIRouter, Request, HTTPException, Query

from app.core.persistence import PersistenceManager
from app.agent.agent import agent
from app.integrations.whatsapp_gateway import wa_gateway

router = APIRouter(prefix="/webhooks/whatsapp", tags=["WhatsApp"])
logger = logging.getLogger(__name__)

VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "kirp-secure-token")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379")
r_client = redis.from_url(REDIS_URL)


@router.get("/")
async def verify_webhook(
    mode: str = Query(..., alias="hub.mode"),
    token: str = Query(..., alias="hub.verify_token"),
    challenge: str = Query(..., alias="hub.challenge"),
):
    """
    WhatsApp webhook verification (Meta standard).
    """
    if mode == "subscribe" and token == VERIFY_TOKEN:
        return int(challenge)
    raise HTTPException(status_code=403, detail="Verification failed")


@router.post("/")
async def receive_whatsapp(request: Request):
    """
    Unified WhatsApp message handler:
    - Supports Meta webhook structure
    - Supports simplified structure
    - Pushes event to Redis queue
    - Sends response via WhatsApp gateway
    """
    try:
        body = await request.json()

        # Try Meta webhook structure
        entry = (
            body.get("entry", [{}])[0]
            .get("changes", [{}])[0]
            .get("value", {})
        )

        if "messages" in entry:
            msg = entry["messages"][0]
            text = msg.get("text", {}).get("body")
            sender = msg.get("from")

        else:
            # Fallback: simple structure
            text = body.get("text")
            sender = body.get("from")

        if not text or not sender:
            return {"status": "ignored"}

        # Resolve user
        db = await PersistenceManager.get_db()
        user = await db.users.find_one({"phone": sender})
        user_id = user["username"] if user else f"wa_{sender[:8]}"

        # Push event to Redis queue
        payload = {
            "type": "whatsapp_msg",
            "data": {
                "text": text,
                "user_id": user_id,
                "source": "WhatsApp",
                "job_id": str(uuid.uuid4()),
                "metadata": {"sender": sender},
            },
        }
        r_client.rpush("kirp_events", json.dumps(payload))

        # Process message with agent
        result_text = await agent.process_task(text[:500], user_id=user_id)

        # Send reply
        wa_gateway.send_message(sender, result_text)

        logger.info(f"WhatsApp [{sender}] → processed")
        return {"status": "processed"}

    except Exception as e:
        logger.error(f"WhatsApp webhook error: {e}")
        return {"status": "error", "detail": str(e)}
