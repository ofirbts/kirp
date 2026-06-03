"""
Command Execution API — Natural language commands.

Uses MetaAgent to route commands to appropriate agents.
POST /command/execute — Body: { query, tenant_id?, space_id?, user_id? }
"""

from __future__ import annotations

import logging
import os
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.core.rag_engine import RAGEngine
from src.core.embedding_provider import embedding_model_name, embedding_provider_name
from src.core.agent_framework import AgentFramework
from src.agents.meta_agent import MetaAgent

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/command", tags=["Command"])


class CommandRequest(BaseModel):
    query: str
    tenant_id: str = "default"
    space_id: str = "private"
    user_id: str = "ofir"


async def _get_meta_agent() -> MetaAgent:
    """Get initialized MetaAgent with all agents registered."""
    from src.agents import (
        pattern_analyzer_spec,
        planner_spec,
        forecaster_spec,
        risk_opportunity_spec,
        schema_structure_spec,
        presentation_spec,
        self_improvement_spec,
    )
    from src.agents.meta_agent import meta_agent_spec
    
    af = AgentFramework()
    for spec in (
        pattern_analyzer_spec,
        planner_spec,
        forecaster_spec,
        risk_opportunity_spec,
        schema_structure_spec,
        presentation_spec,
        self_improvement_spec,
        meta_agent_spec,
    ):
        af.register(spec)
    
    return MetaAgent(af)


@router.post("/execute")
async def execute_command(req: CommandRequest) -> dict[str, Any]:
    """
    Execute natural-language command using MetaAgent routing.
    TEST_E2E expects JSON response.
    """
    try:
        # Initialize components
        rag = RAGEngine(
            qdrant_url=os.getenv("QDRANT_URL", "http://localhost:6333"),
            qdrant_api_key=os.getenv("QDRANT_API_KEY"),
            embedding_provider=embedding_provider_name(),
            embedding_model=embedding_model_name(),
        )
        await rag.connect()
        
        meta = await _get_meta_agent()
        
        # Get RAG context
        rag_resp = await rag.search(
            req.query,
            tenant_id=req.tenant_id,
            space_id=req.space_id,
            user_id=req.user_id,
            limit=5,
        )
        
        # Route command via MetaAgent
        context = {
            "rag_response": rag_resp,
        }
        
        result = await meta.route(
            query=req.query,
            tenant_id=req.tenant_id,
            space_id=req.space_id,
            user_id=req.user_id,
            context=context,
        )
        
        if result.get("ok") is not False:
            # Extract success from agent results
            results = result.get("results", {})
            success = any(r.get("ok") for r in results.values() if isinstance(r, dict))
            return {
                "ok": True,
                "success": success,
                "query": req.query,
                "routing": result.get("routing", {}),
                "results": results,
            }
        else:
            return {
                "ok": False,
                "success": False,
                "query": req.query,
                "error": result.get("error", "Command execution failed"),
            }
    except Exception as e:
        logger.exception("Command execute failed")
        raise HTTPException(status_code=500, detail=str(e))
