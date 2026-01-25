"""
Command Execution API — Natural language commands.

POST /command/execute — Body: { query, tenant_id?, space_id?, user_id? }
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.compat.legacy_agents import CommandExecutorAgent

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/command", tags=["Command"])
executor = CommandExecutorAgent()


class CommandRequest(BaseModel):
    query: str
    tenant_id: str = "default"
    space_id: str = "private"
    user_id: str = "ofir"


@router.post("/execute")
async def execute_command(req: CommandRequest) -> dict[str, Any]:
    """
    Execute natural-language command. TEST_E2E expects JSON response.
    """
    try:
        event = {
            "query": req.query,
            "tenant_id": req.tenant_id,
            "space_id": req.space_id,
            "user_id": req.user_id,
        }
        success = await executor.process_task(event)
        return {"ok": True, "success": success, "query": req.query}
    except Exception as e:
        logger.exception("Command execute failed")
        raise HTTPException(status_code=500, detail=str(e))
