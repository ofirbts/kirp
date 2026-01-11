from typing import List, Dict, Any

class NotionAdapter:
    def enabled(self) -> bool:
        raise NotImplementedError

    def create_task(self, **kwargs) -> None:
        pass

    def get_tasks(self) -> List[Dict[str, Any]]:
        return []

    def get_pending_approvals(self) -> List[Dict[str, Any]]:
        return []

    def update_status(self, page_id: str, status: str) -> None:
        pass
