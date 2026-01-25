from app.imports.base import BaseImporter
from app.services.pipeline import ingest_text


async def run_import(importer: BaseImporter, raw_data: str):
    async for chunk in importer.parse(raw_data):
        await ingest_text(
            text=chunk.content,
            source=chunk.source,
        )
