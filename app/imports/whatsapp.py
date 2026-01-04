import re
from app.imports.base import BaseImporter, ImportChunk


class WhatsAppImporter(BaseImporter):
    """
    Parses WhatsApp exported chat (.txt) into ImportChunks.
    """

    def parse(self, raw_data: str):
        # דוגמה לפורמט טיפוסי של WhatsApp export:
        # 01/01/2025, 10:15 - דניאל: היי, מה קורה?
        pattern = re.compile(r'^(\d{1,2}/\d{1,2}/\d{4}), (\d{1,2}:\d{2}) - (.*?): (.*)$')

        for line in raw_data.splitlines():
            line = line.strip()
            if not line or len(line) < 5:
                continue

            match = pattern.match(line)
            if match:
                date, time, sender, message = match.groups()
                content = f"{sender} אמר/ה: {message} ({date} {time})"

                yield ImportChunk(
                    content=content,
                    source="whatsapp_import"
                )
            else:
                # שורה שלא תואמת פורמט — אפשר לדלג או לשמור כ-is
                continue
