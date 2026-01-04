from app.storage.tasks import tasks_collection

async def fetch_open_tasks():
    cursor = tasks_collection.find({"status": "open"})
    return [task async for task in cursor]

