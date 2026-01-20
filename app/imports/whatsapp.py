import re
from datetime import datetime, timezone
from app.core.persistence import PersistenceManager

class WhatsAppImporter:
    def __init__(self):
        # פורמט: 01/01/2025, 10:15 - שם: הודעה
        self.pattern = re.compile(r'^(\d{1,2}/\d{1,2}/\d{4}), (\d{1,2}:\d{2}) - (.*?): (.*)$')

    async def process_file(self, file_content: str, user_id: str):
        count = 0
        for line in file_content.splitlines():
            match = self.pattern.match(line.strip())
            if match:
                date, time_str, sender, message = match.groups()
                # במקום UnifiedKnowledgeStore, אנחנו יוצרים אירוע במערכת
                await PersistenceManager.append_event(
                    "knowledge_add", 
                    {
                        "text": message,
                        "source": "whatsapp_export",
                        "metadata": {"sender": sender, "date": date, "time": time_str},
                        "user_id": user_id
                    }
                )
                count += 1
        return count