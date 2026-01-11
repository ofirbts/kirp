import os
from datetime import datetime, timedelta

class GoogleCalendarClient:
    def create_event(self, summary: str, start_time: datetime = None):
        # Mock פשוט שעובד (משימה 3)
        if not start_time:
            start_time = datetime.now()
        
        print(f"📅 [MOCK CALENDAR] משריין אירוע: {summary} לזמן: {start_time}")
        return {"status": "success", "event": summary, "time": start_time.isoformat()}

calendar_client = GoogleCalendarClient()
