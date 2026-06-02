"""
Brand API — Personal brand content generation.

Uses PresentationAgent with brand_content view type.
Endpoints: POST /brand/generate, GET /brand/memory.
"""

from __future__ import annotations

import logging
import os
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.core.rag_engine import RAGEngine
from src.core.agent_framework import AgentFramework
from src.agents.presentation import presentation_spec

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/brand", tags=["Brand"])


class ContentRequest(BaseModel):
    idea: str
    user_id: str = "ofir"
    tenant_id: str = "default"
    space_id: str = "private"


@router.post("/generate")
async def generate_content(req: ContentRequest) -> dict[str, Any]:
    """
    Generate LinkedIn-style content from idea using PresentationAgent.
    Returns JSON with headline, body, CTA.
    """
    try:
        # Initialize components
        rag = RAGEngine(qdrant_url=os.getenv("QDRANT_URL", "http://localhost:6333"))
        await rag.connect()
        
        af = AgentFramework()
        af.register(presentation_spec)
        
        # Get RAG context for the idea
        rag_resp = await rag.search(
            req.idea,
            tenant_id=req.tenant_id,
            space_id=req.space_id,
            user_id=req.user_id,
            limit=5,
        )
        
        # Call PresentationAgent with brand_content view type
        context = {
            "rag_response": rag_resp,
            "view_type": "brand_content",
            "idea": req.idea,
        }
        
        result = await af.run(
            "PresentationAgent",
            tenant_id=req.tenant_id,
            space_id=req.space_id,
            user_id=req.user_id,
            context=context,
        )
        
        if result.get("ok"):
            return {"ok": True, **result}
        else:
            raise HTTPException(status_code=500, detail=result.get("error", "Brand generation failed"))
    except Exception as e:
        logger.exception("Brand generate failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/memory")
async def get_memory() -> dict[str, Any]:
    """Brand memory (content + lessons)."""
    try:
        from src.brand.memory import get_memory as _get_memory
        content, lessons = _get_memory()
        return {
            "content": [{"date": c.date, "topic": c.topic, "type": c.type} for c in content],
            "lessons": [{"what_worked": l.what_worked, "what_failed": l.what_failed} for l in lessons],
        }
    except Exception as e:
        logger.exception("Brand memory failed")
        return {"content": [], "lessons": [], "error": str(e)}
