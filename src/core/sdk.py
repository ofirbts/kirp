"""
Thin Python SDK client for KIRP Enterprise.

This is a very small HTTP wrapper intended for internal tools and tests.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

import httpx


@dataclass
class KIRPClient:
    base_url: str
    token: Optional[str] = None

    async def _request(
        self,
        method: str,
        path: str,
        json_body: Optional[dict] = None,
    ) -> Dict[str, Any]:
        url = self.base_url.rstrip("/") + path
        headers: dict[str, str] = {}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        async with httpx.AsyncClient() as client:
            r = await client.request(method, url, json=json_body, headers=headers, timeout=15.0)
        r.raise_for_status()
        if r.content:
            return r.json()
        return {}

    async def login(self, email: str, password: str) -> Dict[str, Any]:
        """Call /api/login and store JWT."""
        data = await self._request(
            "POST",
            "/api/login",
            json_body={"email": email, "password": password},
        )
        token = data.get("token")
        if token:
            self.token = token
        return data

    async def ingest(
        self,
        tenant_id: str,
        space_id: str,
        user_id: str,
        content: str,
        source: str = "sdk",
    ) -> Dict[str, Any]:
        """Wrap /api/v1/ingest."""
        return await self._request(
            "POST",
            "/api/v1/ingest",
            json_body={
                "tenant_id": tenant_id,
                "space_id": space_id,
                "user_id": user_id,
                "content": content,
                "source": source,
            },
        )

    async def list_agents(self) -> Dict[str, Any]:
        """Wrap GET /api/agents."""
        return await self._request("GET", "/api/agents")

