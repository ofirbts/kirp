"""
Calendar Integration — Inbound + Outbound.

- Inbound: events → Events
- Outbound: create/update events
- OAuth: uses refresh_token + client_id/client_secret (env) so tokens can refresh.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

GOOGLE_TOKEN_URI = "https://oauth2.googleapis.com/token"


def _build_calendar_creds(
    access_token: str | None = None,
    refresh_token: str | None = None,
) -> Any:
    """Build Calendar API client credentials; support refresh so expired tokens work."""
    if not access_token and not refresh_token:
        return None
    try:
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
        client_id = os.getenv("GOOGLE_CLIENT_ID")
        client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
        if refresh_token and client_id and client_secret:
            creds = Credentials(
                token=access_token or None,
                refresh_token=refresh_token,
                token_uri=GOOGLE_TOKEN_URI,
                client_id=client_id,
                client_secret=client_secret,
            )
        else:
            creds = Credentials(token=access_token or "")
        return build("calendar", "v3", credentials=creds)
    except Exception as e:
        logger.error("Calendar OAuth init failed: %s", e)
        return None


class CalendarIntegration:
    """Google Calendar / CalDAV. Supports OAuth (with refresh) or service account file."""

    def __init__(self, access_token: str | None = None, token: dict[str, Any] | None = None) -> None:
        self._creds_path = os.getenv("GOOGLE_CREDENTIALS_PATH", "")
        self._token = token
        self._access_token = access_token or (token.get("access_token") if token else None)
        self._refresh_token = token.get("refresh_token") if token else None
        self._client: Any = None

    def connect(self, access_token: str | None = None, token: dict[str, Any] | None = None) -> None:
        t = token or self._token
        access = access_token or (t.get("access_token") if t else None) or self._access_token
        refresh = (t.get("refresh_token") if t else None) or self._refresh_token
        if access or refresh:
            self._client = _build_calendar_creds(access_token=access, refresh_token=refresh)
            if self._client is not None:
                logger.info("CalendarIntegration connected (OAuth)")
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
            # Include last 7 days so recent past events appear in Inbox; default was only "from now"
            now = datetime.now(timezone.utc)
            if since is not None:
                tmin = since.isoformat().replace("+00:00", "Z")
            else:
                from datetime import timedelta
                tmin = (now - timedelta(days=7)).isoformat().replace("+00:00", "Z")

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
