import os
from notion_client import Client
from .base import NotionAdapter

class RealNotionService(NotionAdapter):
    def __init__(self):
        token = os.getenv("NOTION_TOKEN")
        db_id = os.getenv("NOTION_TASKS_DB_ID")

        if not token or token == "mock":
            self.client = None
        else:
            self.client = Client(auth=token)

        self.db_id = db_id

    def enabled(self) -> bool:
        return self.client is not None and self.db_id is not None

    def create_task(self, title: str, **_):
        if not self.enabled():
            return

        self.client.pages.create(
            parent={"database_id": self.db_id},
            properties={
                "Name": {"title": [{"text": {"content": title}}]},
                "Status": {"status": {"name": "Pending"}},
            },
        )
