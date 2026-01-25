"""
Brand API — Personal brand content generation.

Uses compat OrchestratorAgent. Endpoints: POST /brand/generate, GET /brand/memory.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.compat.legacy_agents import OrchestratorAgent, BrandContentRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/brand", tags=["Brand"])


class ContentRequest(BaseModel):
    idea: str
    user_id: str = "ofir"


@router.post("/generate")
async def generate_content(req: ContentRequest) -> dict[str, Any]:
    """Generate LinkedIn-style content from idea. Returns JSON."""
    try:
        orchestrator = OrchestratorAgent()
        result = await orchestrator.generate(
            BrandContentRequest(idea=req.idea, user_id=req.user_id),
        )
        return {"ok": True, **result}
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
