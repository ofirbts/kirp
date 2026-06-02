"""
Scenarios API — Run scenario orchestrator (second_brain_daily, etc.).
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from src.auth.tenant_context import TenantContext, get_effective_tenant_context
from src.agents.orchestrator import get_scenario_orchestrator

router = APIRouter(prefix="/api/v1", tags=["scenarios"])


class ScenarioRunRequest(BaseModel):
    """Accept scenario_id (preferred) or scenario_name for UI/docs consistency."""
    scenario_id: str | None = Field(None, description="Scenario ID (e.g. second_brain_daily)")
    scenario_name: str | None = Field(None, description="Alias for scenario_id")
    context: dict[str, Any] | None = None
    tenant_id: str | None = None
    space_id: str | None = None
    user_id: str | None = None


@router.get("/scenarios")
async def list_scenarios() -> dict:
    """List available scenario IDs from SCENARIOS.md."""
    orch = get_scenario_orchestrator()
    return {"ok": True, "scenarios": orch.list_scenarios()}


@router.post("/scenarios/run")
async def run_scenario(
    body: ScenarioRunRequest,
    ctx: TenantContext = Depends(get_effective_tenant_context),
) -> dict[str, Any]:
    """
    Run a scenario (e.g. second_brain_daily).
    Returns: scenario_id, agents run, outputs, results.
    """
    scenario_id = body.scenario_id or body.scenario_name
    if not scenario_id:
        return {
            "ok": False,
            "error": "scenario_id or scenario_name required",
            "scenario_id": None,
            "agents": [],
            "results": [],
        }
    orch = get_scenario_orchestrator()
    tenant_id = body.tenant_id or ctx.tenant_id
    space_id = body.space_id or ctx.space_id or "all"
    user_id = body.user_id or ctx.user_id
    result = await orch.run(
        scenario_name=scenario_id,
        tenant_id=tenant_id,
        space_id=space_id,
        user_id=user_id,
        initial_context=body.context,
    )
    if not result.get("ok"):
        return result
    agents = orch.get_agents(scenario_id)
    return {
        "ok": True,
        "scenario_id": scenario_id,
        "agents": agents,
        "results": result.get("results", []),
        "context": result.get("context", {}),
    }
