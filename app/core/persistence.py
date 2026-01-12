import os
import uuid
import json
import datetime
from typing import Any, Dict, List, Optional
from app.core.integrations import mongo_db

class PersistenceManager:
    @staticmethod
    def append_event(event_type: str, payload: Dict[str, Any], requires_approval: bool = False) -> str:
        event_id = str(uuid.uuid4())[:8]
        record = {
            "id": event_id,
            "type": event_type,
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "data": payload,
            "status": "pending_approval" if requires_approval else "completed",
            "metadata": {"source": "kirp_core"}
        }
        
        # 1. MongoDB Store
        mongo_db["events"].insert_one(record.copy())
        
        # 2. Local File Backup
        os.makedirs("storage/audit", exist_ok=True)
        with open("storage/audit/events.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
            
        return event_id

    @staticmethod
    def get_all_events(limit: int = 100) -> List[Dict[str, Any]]:
        return list(mongo_db["events"].find({}, {"_id": 0}).sort("timestamp", -1).limit(limit))

    @staticmethod
    def get_pending_approvals() -> List[Dict[str, Any]]:
        return list(mongo_db["events"].find({"status": "pending_approval"}, {"_id": 0}))

    @staticmethod
    def update_event_status(event_id: str, new_status: str, decision_notes: str = "") -> bool:
        result = mongo_db["events"].update_one(
            {"id": event_id},
            {"$set": {
                "status": new_status,
                "resolved_at": datetime.datetime.utcnow().isoformat(),
                "notes": decision_notes
            }}
        )
        return result.modified_count > 0
