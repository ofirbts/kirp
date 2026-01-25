from app.services.notion import notion
from app.core.persistence import PersistenceManager


class ExecutorAgent:
    """
    Executes approved events into concrete actions (e.g., creating tasks in Notion).
    """

    @staticmethod
    async def process_task(event_id: str, user_id: str) -> bool:
        """
        - Fetches events associated only with the given user
        - Verifies the event exists and is approved
        - Creates a Notion task with the event trace ID
        """
        # שליפת אירועים המשויכים אך ורק למשתמש המחובר
        events = PersistenceManager.get_user_events(user_id=user_id)
        event = next((e for e in events if e["id"] == event_id), None)

        # וידוי שהאירוע קיים ומאושר לביצוע
        if event and event.get("status") == "approved":
            title = event["data"].get("task", "Untitled Task")
            # יצירת המשימה ב-Notion עם ה-Trace ID של האירוע
            notion.create_task(
                title=title,
                trace_id=event_id,
                source="KIRP Executor",
            )
            return True

        return False
