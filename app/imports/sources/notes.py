from app.imports.base import BaseImporter, ImportChunk

class NotesImporter(BaseImporter):
    def parse(self, raw_data: str):
        for line in raw_data.splitlines():
            line = line.strip()
            if not line:
                continue
            yield ImportChunk(content=line, source="notes_import")
