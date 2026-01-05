# app/services/memory_intelligence/strength.py
from datetime import datetime, timezone, timedelta
from app.storage.memory import memory_collection

async def decay_memory_strength(days: int = 30, amount: int = 1):
    """
    Reduce strength for memories not updated recently.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    await memory_collection.update_many(
        {"last_updated": {"$lt": cutoff}},
        {"$inc": {"strength": -amount}}
    )

    await memory_collection.delete_many(
        {"strength": {"$lte": 0}}
    )
