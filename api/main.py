"""
Brand OS v3 API — POST /brand-os/run returns final_output_format from EXECUTION_TEMPLATE.
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Any, Optional

from brand_os_sdk import run_orchestrator

app = FastAPI(
    title="Brand OS v3 API",
    version="3.0.0",
    description="Run Brand OS v3 orchestrator; returns final_output_format from EXECUTION_TEMPLATE.",
)


class RunRequest(BaseModel):
    tenant_id: str = Field(..., description="Tenant identifier")
    platform: str = Field(..., description="Platform: linkedin, twitter, or whatsapp")
    topic_hint: str = Field(..., description="Topic hint for content generation")
    trace_id: Optional[str] = Field(None, description="Optional trace ID; generated if omitted")
    extra_context: Optional[dict[str, Any]] = Field(
        None,
        description="Optional signals and memory_entries for context",
    )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "brand-os-v3-api"}


@app.post("/brand-os/run")
def brand_os_run(body: RunRequest) -> dict[str, Any]:
    """
    Run the Brand OS v3 pipeline.
    Returns final_output_format: trace_id, tenant_id, platform, topic_hint, content, visual_spec, recommendations, status.
    """
    payload = {
        "tenant_id": body.tenant_id,
        "platform": body.platform,
        "topic_hint": body.topic_hint,
    }
    if body.trace_id is not None:
        payload["trace_id"] = body.trace_id
    if body.extra_context is not None:
        payload["extra_context"] = body.extra_context
    try:
        result = run_orchestrator(payload)
        return result
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=f"Brand OS config not found: {e}")
    except (KeyError, TypeError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e))
