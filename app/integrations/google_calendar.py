import os
from datetime import datetime, timedelta

class GoogleCalendarClient:
    def create_event(self, summary: str, start_time: datetime = None):
        # Mock פשוט שעובד (משימה 3)
        if not start_time:
            start_time = datetime.now()
        

calendar_client = GoogleCalendarClient()
