from notion_client import Client
import os

class NotionService:
    def __init__(self, auth_token: str):
        self.notion = Client(auth=auth_token)

    async def export_insight_to_page(self, database_id: str, insight_data: dict):
        """יוצר דף חדש ב-Notion עבור תובנה שאושרה"""
        new_page = self.notion.pages.create(
            parent={"database_id": database_id},
            properties={
                "Title": {"title": [{"text": {"content": insight_data['title']}}]},
                "Type": {"select": {"name": insight_data['type']}},
                "Confidence": {"number": insight_data['confidence']}
            },
            children=[
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {"rich_text": [{"type": "text", "text": {"content": insight_data['description']}}]}
                }
            ]
        )
        return new_page