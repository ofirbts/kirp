from .base import NotionAdapter

class NullNotionService(NotionAdapter):
    def enabled(self) -> bool:
        return False

    def create_task(self, title: str, trace_id: str = "N/A", source: str = "KIRP Agent", confidence: float = 1.0):
        return None

    def get_tasks(self):
        return []

    def get_pending_approvals(self):
        return []

    def update_status(self, page_id: str, status: str):
        pass