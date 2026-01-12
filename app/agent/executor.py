from app.services.notion import notion
from app.core.persistence import PersistenceManager

class ExecutorAgent:
    @staticmethod
    async def process_task(event_id: str):
        # שליפת האירוע מה-Persistence
        events = PersistenceManager.get_all_events()
        event = next((e for e in events if e['id'] == event_id), None)
        
        if event and event['status'] == "approved":
            # יצירה ב-Notion
            title = event['data'].get('task', 'Untitled Task')
            notion.create_task(title=title, trace_id=event_id, source="KIRP Executor")
            return True
        return False
