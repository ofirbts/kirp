import logging
import time
from typing import Any, Dict

logger = logging.getLogger(__name__)

class Observability:
    def __init__(self):
        self.start_time = None

    def record_event(self, event_name: str, data: Dict[str, Any] = None):
        """תיקון: הפונקציה שהייתה חסרה"""
        log_msg = f"[OBSERVABILITY] Event: {event_name} | Data: {data or {}}"
        logger.info(log_msg)

    def record_query(self):
        """תמיכה בשם הישן אם קיים בקוד אחר"""
        self.record_event("query_processed")

    def start_timer(self):
        self.start_time = time.time()

    def stop_timer(self, label: str):
        if self.start_time:
            duration = time.time() - self.start_time
            self.record_event("timer_stop", {"label": label, "duration": f"{duration:.4f}s"})
            self.start_time = None

# יצירת סינגלטון לשימוש כללי אם צריך
obs = Observability()
