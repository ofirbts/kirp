from app.models.ingest import IngestRequest
from app.storage.messages import messages_collection
from datetime import datetime

async def ingest_message(data: IngestRequest) -> str:
    document = {
        "source": data.source,
        "content": data.content,
        "timestamp": data.timestamp,
        "created_at": datetime.utcnow()
    }

    result = await messages_collection.insert_one(document)
    return str(result.inserted_id)
