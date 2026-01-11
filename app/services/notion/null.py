from .base import NotionAdapter

class NullNotionService(NotionAdapter):
    def enabled(self) -> bool:
        return False
