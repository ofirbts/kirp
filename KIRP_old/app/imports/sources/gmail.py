from app.imports.base import BaseImporter, ImportChunk
from app.imports.utils.email_parser import parse_email

class GmailImporter(BaseImporter):
    def parse(self, raw_data: str):
        sender, subject, body = parse_email(raw_data)
        content = f"Email from {sender}: {subject}\n{body}"
        yield ImportChunk(content=content, source="gmail_import")
