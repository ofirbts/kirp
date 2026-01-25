from app.imports.base import BaseImporter, ImportChunk


class TextImporter(BaseImporter):

    def parse(self, raw_data: str):
        lines = raw_data.splitlines()

        for line in lines:
            line = line.strip()
            if len(line) < 5:
                continue

            yield ImportChunk(
                content=line,
                source="text_import"
            )
