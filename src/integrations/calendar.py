"""
Calendar Integration — Inbound + Outbound.

- Inbound: events → Events
- Outbound: create/update events
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


class CalendarIntegration:
    """Google Calendar / CalDAV. Supports OAuth access_token or service account file."""

    def __init__(self, access_token: str | None = None) -> None:
        import os
        self._creds_path = os.getenv("GOOGLE_CREDENTIALS_PATH", "")
        self._access_token = access_token
        self._client: Any = None

    def connect(self, access_token: str | None = None) -> None:
        token = access_token or self._access_token
        if token:
            try:
                from google.oauth2.credentials import Credentials
                from googleapiclient.discovery import build
                creds = Credentials(token=token)
                self._client = build("calendar", "v3", credentials=creds)
                logger.info("CalendarIntegration connected (OAuth)")
                return
            except Exception as e:
                logger.error("Calendar OAuth init failed: %s", e)
                return
        if not self._creds_path:
            logger.warning("Calendar credentials missing")
            return
        try:
            from google.oauth2 import service_account
            from googleapiclient.discovery import build
            creds = service_account.Credentials.from_service_account_file(self._creds_path)
            self._client = build("calendar", "v3", credentials=creds)
            logger.info("CalendarIntegration connected")
        except Exception as e:
            logger.error("Calendar init failed: %s", e)

    async def list_events(
        self,
        tenant_id: str,
        space_id: str,
        user_id: str,
        calendar_id: str = "primary",
        since: datetime | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Fetch calendar events as ingestion payloads."""
        import asyncio
        if not self._client:
            self.connect()
        if not self._client:
            return []
        events: list[dict[str, Any]] = []
        try:
            tmin = (since or datetime.now(timezone.utc)).isoformat() + "Z"

            def _list() -> dict:
                return self._client.events().list(
                    calendarId=calendar_id,
                    timeMin=tmin,
                    maxResults=limit,
                    singleEvents=True,
                    orderBy="startTime",
                ).execute()

            r = await asyncio.to_thread(_list)
            for ev in r.get("items", []):
                ev_id = ev.get("id")
                start = ev.get("start", {}).get("dateTime") or ev.get("start", {}).get("date", "")
                events.append({
                    "tenant_id": tenant_id,
                    "space_id": space_id,
                    "user_id": user_id,
                    "source": "calendar",
                    "content": ev.get("summary", "") + "\n" + (ev.get("description") or ""),
                    "metadata": {"external_id": ev_id, "id": ev_id, "start": start, "calendar": calendar_id},
                })
        except Exception as e:
            logger.error("Calendar list failed: %s", e)
        return events

    async def create_event(
        self,
        calendar_id: str,
        summary: str,
        start: datetime,
        end: datetime,
        user_id: str = "system",
    ) -> dict[str, Any]:
        """Create calendar event. Outbound action."""
        if not self._client:
            self.connect()
        if not self._client:
            return {"ok": False, "error": "Calendar not configured"}
        try:
            body = {
                "summary": summary,
                "start": {"dateTime": start.isoformat(), "timeZone": "UTC"},
                "end": {"dateTime": end.isoformat(), "timeZone": "UTC"},
            }
            ev = self._client.events().insert(calendarId=calendar_id, body=body).execute()
            return {"ok": True, "id": ev.get("id")}
        except Exception as e:
            logger.error("Calendar create failed: %s", e)
            return {"ok": False, "error": str(e)}
