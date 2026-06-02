"""
Brand OS — Templates, brand memory, tone consistency, content library, multi-channel.

- Brand templates (email, WhatsApp, social)
- Brand memory (Qdrant + Redis)
- Tone consistency engine
- Content library
- Multi-channel output
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


@dataclass
class BrandTemplate:
    """Template for a channel (email, whatsapp, social)."""

    id: str
    tenant_id: str
    name: str
    channel: str  # email | whatsapp | linkedin | twitter
    subject_key: str | None = None
    body_template: str = ""
    tone: str = "professional"
    variables: list[str] = None

    def __post_init__(self) -> None:
        if self.variables is None:
            self.variables = []


@dataclass
class BrandMemory:
    """Brand memory entry (voice, guidelines)."""

    id: str
    tenant_id: str
    content: str
    kind: str = "guideline"  # guideline | voice | example
    channel: str | None = None
    created_at: datetime | None = None


class BrandEngine:
    """
    Brand templates, memory, tone consistency, content library.
    """

    def __init__(self, qdrant_url: str, redis_url: str) -> None:
        self._qdrant_url = qdrant_url
        self._redis_url = redis_url
        self._templates: dict[str, BrandTemplate] = {}
        self._memory: dict[str, list[BrandMemory]] = {}

    async def get_template(self, tenant_id: str, name: str, channel: str) -> BrandTemplate | None:
        key = f"{tenant_id}:{channel}:{name}"
        return self._templates.get(key)

    async def list_templates(self, tenant_id: str, channel: str | None = None) -> list[BrandTemplate]:
        out = [t for t in self._templates.values() if t.tenant_id == tenant_id]
        if channel:
            out = [t for t in out if t.channel == channel]
        return out

    async def save_template(self, t: BrandTemplate) -> None:
        key = f"{t.tenant_id}:{t.channel}:{t.name}"
        self._templates[key] = t

    async def get_brand_memory(self, tenant_id: str, kind: str | None = None) -> list[BrandMemory]:
        key = tenant_id
        entries = self._memory.get(key, [])
        if kind:
            entries = [e for e in entries if e.kind == kind]
        return entries

    async def add_brand_memory(self, tenant_id: str, content: str, kind: str = "guideline", channel: str | None = None) -> str:
        mid = str(uuid4())
        entry = BrandMemory(id=mid, tenant_id=tenant_id, content=content, kind=kind, channel=channel, created_at=datetime.now(timezone.utc))
        self._memory.setdefault(tenant_id, []).append(entry)
        return mid

    async def render(self, tenant_id: str, channel: str, template_name: str, variables: dict[str, str]) -> dict[str, str]:
        """Render template with variables. Returns subject (if any) and body."""
        t = await self.get_template(tenant_id, template_name, channel)
        if not t:
            return {"subject": "", "body": ""}
        body = t.body_template
        for k, v in variables.items():
            body = body.replace("{{" + k + "}}", str(v))
        subject = (t.subject_key and variables.get(t.subject_key)) or ""
        return {"subject": subject, "body": body}
