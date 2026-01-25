from datetime import datetime, timezone
from app.integrations.google_calendar import GoogleCalendarClient

class CalendarService:
    @staticmethod
    def extract_and_create(text: str) -> list:
        # דמו חכם – בהמשך NLP
        event = {
            "summary": "Event from KIRP",
            "description": text,
            "start": datetime.now(timezone.utc).isoformat(),
            "end": datetime.now(timezone.utc).isoformat()
        }

        client = GoogleCalendarClient()
        created = client.create_event(event)

        return [created]
