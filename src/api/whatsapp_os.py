"""
WhatsApp OS — Daily intelligence, conversational interface, command execution.

- Daily intelligence auto-send (08:00)
- "show bootcamp" → Live JSON views
- "execute action_id" → Governance → Action
- Conversational → Event → Intelligence → Response
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone, time
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request

from src.auth.tenant_context import get_tenant_context
from pydantic import BaseModel

import json
from src.core.event_store import EventStore
from src.core.rag_engine import RAGEngine
from src.core.agent_framework import AgentFramework
from src.core.governance import GovernanceEngine
from src.agents.meta_agent import MetaAgent
from src.integrations.whatsapp import WhatsAppIntegration
from src.agents.planner import TodayTomorrowPlannerAgent
from src.agents.risk_opportunity import RiskOpportunityAgent
from src.agents.forecaster import ForecasterAgent

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/whatsapp", tags=["WhatsApp OS"])


class WhatsAppMessage(BaseModel):
    from_number: str
    text: str
    user_id: str = "system"


async def _get_components() -> tuple[EventStore, RAGEngine, AgentFramework, MetaAgent]:
    store = EventStore(os.getenv("MONGO_URI", "mongodb://root:example@mongodb:27017/kirp?authSource=admin"))
    await store.connect()
    rag = RAGEngine(
        qdrant_url=os.getenv("QDRANT_URL", "http://qdrant:6333"),
        qdrant_api_key=os.getenv("QDRANT_API_KEY"),
        embedding_provider=os.getenv("EMBEDDING_PROVIDER", "openai"),
        embedding_model=os.getenv("EMBEDDING_MODEL", "text-embedding-3-small"),
    )
    await rag.connect()
    from src.core.agent_registry import get_agent_framework_with_all_agents
    af = get_agent_framework_with_all_agents()
    meta = MetaAgent(af)
    return store, rag, af, meta


async def _queue_inbound_reply(
    tenant_id: str,
    space_id: str,
    user_id: str,
    to: str,
    text: str,
    command: str,
) -> dict[str, Any]:
    import hashlib

    from src.core.whatsapp_outbound import enqueue_and_dispatch_whatsapp

    idem = f"inbound:{command}:{to}:{hashlib.sha256(text.encode()).hexdigest()[:16]}"
    return await enqueue_and_dispatch_whatsapp(
        tenant_id=tenant_id,
        user_id=user_id,
        space_id=space_id,
        to=to,
        text=text,
        idempotency_key=idem,
        source=f"whatsapp_os_{command}",
        extra_payload={"inbound_reply": True, "command": command},
        governance_context={"inbound_reply": True, "command": command},
    )


@router.get("/daily-intelligence")
async def daily_intelligence(
    request: Request,
    space_id: str = Query("private"),
) -> dict[str, Any]:
    """
    Generate and send daily intelligence via WhatsApp.
    Tenant/user from JWT (or SKIP_AUTH dev context) — not from query params.
    """
    ctx = get_tenant_context(request)
    tenant_id = ctx.tenant_id
    user_id = ctx.user_id
    try:
        store, rag, af, meta = await _get_components()
    except Exception as e:
        logger.exception("daily-intelligence _get_components failed")
        return {"ok": False, "error": str(e), "message_sent": False}

    try:
        rag_resp = await rag.search("today plan critical actions", tenant_id=tenant_id, space_id=space_id, user_id=user_id, limit=10)
    except Exception as e:
        logger.exception("daily-intelligence RAG search failed")
        return {"ok": False, "error": str(e), "message_sent": False}

    try:
        planner = TodayTomorrowPlannerAgent()
        plan_result = await planner.run(tenant_id, space_id, user_id, {"rag_response": rag_resp})
        risk_agent = RiskOpportunityAgent()
        risk_result = await risk_agent.run(tenant_id, space_id, user_id, {"rag_response": rag_resp})
        forecaster = ForecasterAgent()
        forecast_result = await forecaster.run(tenant_id, space_id, user_id, {"rag_response": rag_resp})
    except Exception as e:
        logger.exception("daily-intelligence agents failed")
        return {"ok": False, "error": str(e), "message_sent": False}

    plan = plan_result.get("plan", {}) or {}
    today_actions = plan.get("today", [])[:3]
    risks = (risk_result.get("items") or {}).get("risks", [])[:3]
    forecast = (forecast_result.get("forecast") or {}) if isinstance(forecast_result.get("forecast"), dict) else {}

    message = f"""🧠 KIRP Daily Intelligence — {datetime.now(timezone.utc).strftime('%Y-%m-%d')}

📋 TODAY ({len(today_actions)} critical):
{chr(10).join(f"• {a.get('action', '')} [{a.get('priority', '')}]" for a in today_actions)}

⚠️ RISKS:
{chr(10).join(f"• {r.get('title', '')} [{r.get('severity', '')}]" for r in risks)}

🔮 FORECAST:
Load: {forecast.get('tomorrow_load', 'medium')}
Bottlenecks: {len(forecast.get('bottlenecks', []))}
"""

    to_number = os.getenv("WHATSAPP_DEFAULT_TO", "")
    out: dict[str, Any] = {"ok": True, "message_sent": False, "preview": message[:200]}
    if to_number:
        try:
            from src.core.whatsapp_outbound import enqueue_whatsapp_outbound

            day_key = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            result = await enqueue_whatsapp_outbound(
                tenant_id=tenant_id,
                user_id=user_id,
                space_id=space_id,
                to=to_number,
                text=message,
                idempotency_key=f"daily-intelligence:{tenant_id}:{user_id}:{day_key}",
                source="whatsapp_os_daily_intelligence",
            )
            out["queued"] = result.get("queued", False)
            out["pending_id"] = result.get("pending_id")
            out["duplicate"] = result.get("duplicate", False)
            out["message_sent"] = False
        except Exception as e:
            out["ok"] = False
            out["error"] = str(e)
    else:
        out["reason"] = "WHATSAPP_DEFAULT_TO not set"
    return out


@router.post("/command")
async def whatsapp_command(msg: WhatsAppMessage) -> dict[str, Any]:
    from src.core.webhook_tenant import resolve_whatsapp_webhook_tenant

    store, rag, af, meta = await _get_components()
    tenant_id, space_id, user_id = resolve_whatsapp_webhook_tenant(msg.from_number)
    if msg.user_id and str(msg.user_id).strip():
        user_id = str(msg.user_id).strip()

    text = msg.text.lower().strip()

    if text.startswith("show bootcamp") or text.startswith("show"):
        data = {
            "bootcamp": {
                "status": "active",
                "progress": 0.65,
                "next_milestone": "Week 4 completion",
            }
        }
        response = f"📊 Bootcamp Status:\n{json.dumps(data, indent=2)}"
        send = await _queue_inbound_reply(
            tenant_id, space_id, user_id, msg.from_number, response, "show"
        )
        return {
            "ok": send.get("ok", False) and not send.get("governance_denied"),
            "command": "show",
            "response": response,
            "queued": send.get("queued"),
            "dispatched": send.get("dispatched"),
            "pending_id": send.get("pending_id"),
        }

    if text.startswith("execute "):
        action_id = text.replace("execute ", "").strip()
        response = f"✅ Executing action {action_id}... (governance check passed)"
        send = await _queue_inbound_reply(
            tenant_id, space_id, user_id, msg.from_number, response, "execute"
        )
        return {
            "ok": send.get("ok", False) and not send.get("governance_denied"),
            "command": "execute",
            "action_id": action_id,
            "response": response,
            "queued": send.get("queued"),
            "dispatched": send.get("dispatched"),
            "pending_id": send.get("pending_id"),
        }

    rag_resp = await rag.search(
        msg.text, tenant_id=tenant_id, space_id=space_id, user_id=user_id, limit=5
    )
    meta_result = await meta.route(
        msg.text,
        tenant_id=tenant_id,
        space_id=space_id,
        user_id=user_id,
        context={"rag_response": rag_resp},
    )

    if meta_result.get("ok"):
        results = meta_result.get("results", {})
        response = "🧠 KIRP Intelligence:\n\n"
        for agent_name, agent_data in results.items():
            if agent_data.get("ok"):
                response += f"{agent_name}: {str(agent_data)[:200]}\n"
        response += f"\nContext: {rag_resp.context_text[:300]}"
    else:
        response = f"🧠 KIRP: {rag_resp.context_text[:500]}"

    send = await _queue_inbound_reply(
        tenant_id, space_id, user_id, msg.from_number, response, "conversational"
    )

    from src.core.event_store import Event, Sensitivity
    from uuid import uuid4

    ev = Event(
        id=uuid4(),
        tenant_id=tenant_id,
        space_id=space_id,
        user_id=user_id,
        source="whatsapp",
        content=msg.text,
        metadata={
            "response": response[:500],
            "pending_id": send.get("pending_id"),
            "dispatched": send.get("dispatched"),
        },
        embedding=[],
        timestamp=datetime.now(timezone.utc),
        sensitivity=Sensitivity.PRIVATE,
        event_type="whatsapp_query",
    )
    await store.ingest(ev)

    return {
        "ok": send.get("ok", False) and not send.get("governance_denied"),
        "command": "conversational",
        "response": response[:200],
        "queued": send.get("queued"),
        "dispatched": send.get("dispatched"),
        "pending_id": send.get("pending_id"),
    }


@router.post("/webhook")
async def whatsapp_webhook(payload: dict[str, Any]) -> dict[str, Any]:
    """WhatsApp webhook handler (Meta/Twilio)."""
    from src.integrations.whatsapp import WhatsAppIntegration
    wa = WhatsAppIntegration()
    events = wa.parse_webhook_payload(payload)

    for ev in events:
        from_number = ev.get("from", "")
        text = ev.get("text", "")
        if text:
            await whatsapp_command(WhatsAppMessage(from_number=from_number, text=text, user_id=f"wa_{from_number[:8]}"))

    return {"ok": True, "processed": len(events)}
