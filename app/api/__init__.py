from . import health, ingest, ingest_batch, debug, query
from .agent import router as agent_router

# הערה: tasks הוסר זמנית עד שנבנה storage.tasks מלא
print("✅ API modules loaded (tasks disabled temporarily)")
