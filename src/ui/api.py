"""
API Client — HTTP client for KIRP API.

Used by Streamlit dashboard and other UI consumers.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class KIRPApiClient:
    """HTTP client for KIRP Enterprise API."""

    def __init__(self, base_url: str, token: str | None = None) -> None:
        self._base = base_url.rstrip("/")
        self._token = token

    def _headers(self) -> dict[str, str]:
        h: dict[str, str] = {"Content-Type": "application/json"}
        if self._token:
            h["Authorization"] = f"Bearer {self._token}"
        return h

    async def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any] | list[Any]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.request(
                method,
                f"{self._base}{path}",
                headers=self._headers(),
                **kwargs,
            )
            r.raise_for_status()
            return r.json() if r.content else {}

    async def health(self) -> dict[str, Any]:
        """GET /health"""
        out = await self._request("GET", "/health")
        return out if isinstance(out, dict) else {}

    async def stats(self) -> dict[str, Any]:
        """GET /api/v1/stats (dashboard summary)."""
        out = await self._request("GET", "/api/v1/stats")
        return out if isinstance(out, dict) else {}

    async def ingest(
        self,
        tenant_id: str,
        space_id: str,
        user_id: str,
        content: str,
        source: str = "ui",
    ) -> dict[str, Any]:
        """POST /api/v1/ingest"""
        out = await self._request(
            "POST",
            "/api/v1/ingest",
            json={
                "tenant_id": tenant_id,
                "space_id": space_id,
                "user_id": user_id,
                "content": content,
                "source": source,
            },
        )
        return out if isinstance(out, dict) else {}

    async def query(
        self,
        query: str,
        k: int = 6,
    ) -> dict[str, Any]:
        """POST /api/v1/query — tenant/space/user from JWT or SKIP_AUTH (not request body)."""
        out = await self._request(
            "POST",
            "/api/v1/query",
            json={"query": query, "k": k},
        )
        return out if isinstance(out, dict) else {}

    async def agents(self) -> list[dict[str, Any]]:
        """GET /api/v1/agents"""
        out = await self._request("GET", "/api/v1/agents")
        return out if isinstance(out, list) else []

    async def insights(self, tenant_id: str, user_id: str) -> list[dict[str, Any]]:
        """GET /api/v1/insights"""
        out = await self._request(
            "GET",
            f"/api/v1/insights?tenant_id={tenant_id}&user_id={user_id}",
        )
        return out if isinstance(out, list) else []
