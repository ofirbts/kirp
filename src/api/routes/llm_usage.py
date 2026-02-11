"""
LLM Usage API — aggregate usage/cost across providers.

Endpoint:
- GET /api/v1/llm/usage

Notes:
- This is observability/ops-only data; it does not call LLMs directly.
- External calls are read‑only and scoped to provider dashboard/usage APIs.
"""

from __future__ import annotations

import os
from typing import Any, Dict

import httpx
from fastapi import APIRouter, Depends

from src.core.jwt_utils import require_auth


router = APIRouter(tags=["LLM Usage"])


async def _safe_get_json(
    url: str,
    headers: Dict[str, str],
    timeout: float = 10.0,
) -> Dict[str, Any]:
    """Helper: perform a GET and return JSON or error without raising."""
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            r = await client.get(url, headers=headers)
            r.raise_for_status()
            return {"status": "ok", "raw": r.json()}
    except Exception as e:  # pragma: no cover - network errors are environment‑specific
        return {"status": "error", "error": str(e)}


async def fetch_groq_usage() -> Dict[str, Any]:
    key = os.getenv("GROQ_API_KEY")
    if not key:
        return {"status": "missing_key"}

    # Groq dashboard usage API (shape may evolve; we keep it best‑effort).
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(
                "https://api.groq.com/dashboard/api/usage",
                headers={"Authorization": f"Bearer {key}"},
            )
            r.raise_for_status()
            data = r.json()
    except Exception as e:  # pragma: no cover - network errors are environment‑specific
        return {"status": "error", "error": str(e)}

    return {
        "status": "ok",
        "tokens_in": data.get("tokens_in"),
        "tokens_out": data.get("tokens_out"),
        "cost_usd": data.get("cost_usd"),
        "raw": data,
    }


async def fetch_openai_usage() -> Dict[str, Any]:
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        return {"status": "missing_key"}

    # OpenAI usage API — exact path/shape may differ per account/plan.
    return await _safe_get_json(
        "https://api.openai.com/v1/usage",
        headers={"Authorization": f"Bearer {key}"},
    )


async def fetch_anthropic_usage() -> Dict[str, Any]:
    key = os.getenv("ANTHROPIC_API_KEY")
    if not key:
        return {"status": "missing_key"}

    # Anthropic usage API — placeholder path; shape may differ.
    return await _safe_get_json(
        "https://api.anthropic.com/v1/usage",
        headers={"x-api-key": key},
    )


async def fetch_gemini_usage() -> Dict[str, Any]:
    key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not key:
        return {"status": "missing_key"}

    # Google/Gemini usage APIs are more fragmented; keep as not implemented for now.
    return {"status": "not_implemented"}


@router.get("/llm/usage")
async def llm_usage(
    _auth: Dict[str, Any] = Depends(require_auth),
) -> Dict[str, Any]:
    """
    Aggregate usage across Groq, OpenAI, Anthropic, Gemini.

    - Requires valid JWT (same as other /api/v1 endpoints).
    - Does NOT expose raw API keys.
    """
    groq, openai, anthropic, gemini = await fetch_groq_usage(), await fetch_openai_usage(), await fetch_anthropic_usage(), await fetch_gemini_usage()

    # Recommendation logic (best‑effort heuristic).
    # When cost field is missing, fall back to a large sentinel so it won't be chosen.
    costs: Dict[str, float] = {
        "groq": float(groq.get("cost_usd") or 999.0),
        "openai": float(
            (openai.get("raw") or {}).get("total_usage") or 999.0
        ),
        "anthropic": float(
            (anthropic.get("raw") or {}).get("total_usage") or 999.0
        ),
    }
    best = min(costs, key=costs.get)

    return {
        "groq": groq,
        "openai": openai,
        "anthropic": anthropic,
        "gemini": gemini,
        "recommendation": f"{best} is the cheapest provider right now",
    }

