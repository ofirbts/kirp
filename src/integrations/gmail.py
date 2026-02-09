"""
Gmail Integration — Inbound ingest via Gmail API.

- OAuth2 tokens from ConnectorTokenStore (or env GOOGLE_CREDENTIALS_PATH for service account).
- Pull-based sync: fetch recent messages → unified event payloads with external_id=message_id.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def _build_client(credentials_path: str | None = None, access_token: str | None = None):
    """Build Gmail API client from service account file or OAuth access_token."""
    if access_token:
        try:
            from google.oauth2.credentials import Credentials
            from googleapiclient.discovery import build
            creds = Credentials(token=access_token)
            return build("gmail", "v1", credentials=creds)
        except Exception as e:
            logger.error("Gmail OAuth client failed: %s", e)
            return None
    if credentials_path:
        try:
            from google.oauth2 import service_account
            from googleapiclient.discovery import build
            creds = service_account.Credentials.from_service_account_file(credentials_path)
            return build("gmail", "v1", credentials=creds)
        except Exception as e:
            logger.error("Gmail service account failed: %s", e)
            return None
    return None


class GmailIntegration:
    """Gmail API: list messages, return unified ingest payloads (idempotent by message id)."""

    def __init__(
        self,
        credentials_path: str | None = None,
        access_token: str | None = None,
    ) -> None:
        import os
        self._creds_path = credentials_path or os.getenv("GOOGLE_CREDENTIALS_PATH", "")
        self._access_token = access_token
        self._client: Any = None

    def connect(self, access_token: str | None = None) -> None:
        token = access_token or self._access_token
        self._client = _build_client(credentials_path=self._creds_path or None, access_token=token)
        if self._client is not None:
            logger.info("GmailIntegration connected")

    async def list_messages(
        self,
        tenant_id: str,
        space_id: str,
        user_id: str,
        max_results: int = 50,
        label_ids: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Fetch recent messages and return unified event payloads for /api/v1/ingest.
        Each payload has source=gmail, metadata.external_id=message_id (for idempotency).
        """
        if self._client is None:
            self.connect()
        if self._client is None:
            return []
        import asyncio
        events: list[dict[str, Any]] = []
        try:
            def _list() -> dict:
                return self._client.users().messages().list(
                    userId="me",
                    maxResults=max_results,
                    labelIds=label_ids or ["INBOX"],
                ).execute()

            r = await asyncio.to_thread(_list)
            for msg_ref in r.get("messages", []):
                msg_id = msg_ref.get("id")
                if not msg_id:
                    continue
                def _get():
                    return self._client.users().messages().get(userId="me", id=msg_id, format="metadata").execute()
                msg = await asyncio.to_thread(_get)
                headers = {h["name"].lower(): h["value"] for h in msg.get("payload", {}).get("headers", [])}
                subject = headers.get("subject", "")
                snippet = msg.get("snippet", "")
                content = f"Subject: {subject}\n\n{snippet}"
                events.append({
                    "tenant_id": tenant_id,
                    "space_id": space_id,
                    "user_id": user_id,
                    "source": "gmail",
                    "content": content[:50000],
                    "metadata": {
                        "external_id": msg_id,
                        "thread_id": msg.get("threadId"),
                        "subject": subject,
                        "from": headers.get("from"),
                        "date": headers.get("date"),
                    },
                })
        except Exception as e:
            logger.error("Gmail list failed: %s", e)
        return events
