import asyncio
from app.imports.whatsapp import WhatsAppImporter
from app.services.import_service import run_import

async def main():
    with open("whatsapp_chat.txt", "r", encoding="utf-8") as f:
        raw_data = f.read()

    importer = WhatsAppImporter()
    await run_import(importer, raw_data)

if __name__ == "__main__":
    asyncio.run(main())
