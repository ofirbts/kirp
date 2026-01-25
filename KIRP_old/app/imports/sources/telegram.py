from bs4 import BeautifulSoup
from app.imports.base import BaseImporter, ImportChunk

class TelegramImporter(BaseImporter):
    def parse(self, raw_data: str):
        soup = BeautifulSoup(raw_data, "html.parser")
        for msg in soup.select(".message"):
            sender = msg.select_one(".from_name")
            text = msg.select_one(".text")
            if not text:
                continue
            content = f"{sender.text if sender else 'Unknown'}: {text.text}"
            yield ImportChunk(content=content, source="telegram_import")
