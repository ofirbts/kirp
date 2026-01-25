import json
from app.imports.base import BaseImporter, ImportChunk
from app.imports.utils.slack_utils import format_slack_message

class SlackImporter(BaseImporter):
    def parse(self, raw_data: str):
        messages = json.loads(raw_data)
        for msg in messages:
            user = msg.get("user", "Unknown")
            text = msg.get("text", "")
            ts = msg.get("ts", "")
            content = format_slack_message(user, text, ts)
            yield ImportChunk(content=content, source="slack_import")
