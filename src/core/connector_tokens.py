"""
Connector token storage — OAuth and API tokens per tenant/user/integration.

Stored in MongoDB (collection connector_tokens), encrypted at rest.
Used by Gmail, Calendar, Notion, Slack, etc. for pull-based sync.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

INTEGRATIONS = ("gmail", "calendar", "notion", "slack", "whatsapp", "email", "webhook")


class ConnectorTokenStore:
    """
    Store and retrieve OAuth/API tokens per (tenant_id, user_id, integration).
    Tokens are encrypted at rest using EncryptionEngine.
    """

    def __init__(self, mongo_uri: str, db_name: str = "kirp") -> None:
        self._mongo_uri = mongo_uri
        self._db_name = db_name
        self._client: Any = None
        self._db: Any = None
        from src.auth.encryption import EncryptionEngine
        self._enc = EncryptionEngine()

    async def connect(self) -> None:
        try:
            from motor.motor_asyncio import AsyncIOMotorClient
            self._client = AsyncIOMotorClient(self._mongo_uri)
            self._db = self._client[self._db_name]
            await self._db.command("ping")
            logger.info("ConnectorTokenStore connected")
        except Exception as e:
            logger.error("ConnectorTokenStore connection failed: %s", e)
            raise

    def _coll(self):
        if self._db is None:
            raise RuntimeError("ConnectorTokenStore not connected")
        return self._db.connector_tokens

    async def set_token(
        self,
        tenant_id: str,
        user_id: str,
        integration: str,
        access_token: str,
        refresh_token: str | None = None,
        expires_at: datetime | None = None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        """Upsert token for (tenant_id, user_id, integration). Encrypts before storing."""
        if integration not in INTEGRATIONS:
            logger.warning("Unknown integration: %s", integration)
        now = datetime.now(timezone.utc)
        doc = {
            "tenant_id": tenant_id,
            "user_id": user_id,
            "integration": integration,
            "access_token_enc": self._enc.encrypt(access_token),
            "updated_at": now,
        }
        if refresh_token:
            doc["refresh_token_enc"] = self._enc.encrypt(refresh_token)
        if expires_at:
            doc["expires_at"] = expires_at.isoformat()
        if extra:
            doc["extra"] = extra
        await self._coll().update_one(
            {"tenant_id": tenant_id, "user_id": user_id, "integration": integration},
            {"$set": doc},
            upsert=True,
        )
        logger.debug("Token set for %s/%s/%s", tenant_id, user_id, integration)

    async def get_token(
        self,
        tenant_id: str,
        user_id: str,
        integration: str,
    ) -> dict[str, Any] | None:
        """Return decrypted token record or None. Keys: access_token, refresh_token?, expires_at?, extra?."""
        doc = await self._coll().find_one({
            "tenant_id": tenant_id,
            "user_id": user_id,
            "integration": integration,
        })
        if not doc:
            return None
        try:
            return {
                "access_token": self._enc.decrypt(doc["access_token_enc"]),
                "refresh_token": self._enc.decrypt(doc["refresh_token_enc"]) if doc.get("refresh_token_enc") else None,
                "expires_at": doc.get("expires_at"),
                "extra": doc.get("extra") or {},
            }
        except Exception as e:
            logger.warning("Token decrypt failed for %s/%s/%s: %s", tenant_id, user_id, integration, e)
            return None

    async def delete_token(self, tenant_id: str, user_id: str, integration: str) -> bool:
        """Remove token. Returns True if a document was deleted."""
        r = await self._coll().delete_one({
            "tenant_id": tenant_id,
            "user_id": user_id,
            "integration": integration,
        })
        return r.deleted_count > 0

    async def list_connected(self, tenant_id: str, user_id: str) -> list[str]:
        """Return list of integration names that have a token for this tenant/user."""
        cursor = self._coll().find(
            {"tenant_id": tenant_id, "user_id": user_id},
            {"integration": 1},
        )
        return [d["integration"] async for d in cursor]
