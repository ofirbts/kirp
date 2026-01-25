from app.imports.base import BaseImporter, ImportChunk
from app.imports.utils.whatsapp_utils import parse_whatsapp_line

class WhatsAppImporter(BaseImporter):
    def parse(self, raw_data: str):
        for line in raw_data.splitlines():
            line = line.strip()
            if not line or len(line) < 5:
                continue
            parsed = parse_whatsapp_line(line)
            if parsed:
                sender, message, timestamp = parsed
                content = f"{sender} אמר/ה: {message} ({timestamp})"
                yield ImportChunk(content=content, source="whatsapp_import")
