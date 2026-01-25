# app/integrations/google_calendar.py
"""
KIRP Google Calendar Integration v3
- יצירת אירועים ביומן
- תמיכה ב-default timezone
- תמיכה ב-start_time אוטומטי אם לא סופק
- מוכן לשילוב עם intent CALENDAR
"""

import os
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class GoogleCalendarClient:
    """
    Minimal but production-ready Google Calendar client.
    Currently uses a mock implementation.
    Future: integrate with Google Calendar API (OAuth2).
    """

    def __init__(self):
        self.default_timezone = os.getenv("CALENDAR_TZ", "UTC")

    def create_event(
        self,
        summary: str,
        start_time: Optional[datetime] = None,
        duration_minutes: int = 30,
        user_id: str = "system",
    ) -> Dict[str, Any]:
        """
        Create a calendar event.
        Currently mocked, but structured for future real API integration.
        """

        if not start_time:
            start_time = datetime.now(timezone.utc)

        end_time = start_time + timedelta(minutes=duration_minutes)

        event = {
            "summary": summary,
            "start": start_time.isoformat(),
            "end": end_time.isoformat(),
            "user_id": user_id,
            "status": "mock_created",
        }

        logger.info(
            f"📅 [MOCK CALENDAR] Event created for {user_id}: "
            f"{summary} @ {start_time.isoformat()}"
        )

        return event


# Singleton instance
calendar_client = GoogleCalendarClient()
