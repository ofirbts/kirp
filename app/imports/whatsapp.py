import re
from typing import List
from app.services.knowledge import UnifiedKnowledgeStore

class WhatsAppImporter:
    """ייבוא היסטוריית צ'אט מקובץ TXT לתוך ה-Knowledge Base"""
    def __init__(self):
        self.store = UnifiedKnowledgeStore()
        # פורמט: 01/01/2025, 10:15 - שם: הודעה
        self.pattern = re.compile(r'^(\d{1,2}/\d{1,2}/\d{4}), (\d{1,2}:\d{2}) - (.*?): (.*)$')

    def process_file(self, file_content: str, user_id: str):
        count = 0
        for line in file_content.splitlines():
            match = self.pattern.match(line.strip())
            if match:
                date, time, sender, message = match.groups()
                content = f"היסטוריית וואטסאפ - {sender}: {message} ({date})"
                # הוספה ישירה ל-Vector Store של המערכת
                self.store.add(content=content, source="whatsapp_export", user_id=user_id)
                count += 1
        return count