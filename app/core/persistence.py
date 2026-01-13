import os
import uuid
import json
import datetime
from typing import Any, Dict, List, Optional
from app.core.integrations import mongo_db
from pymongo import MongoClient

raw_uri = os.getenv("MONGO_URI", "mongodb://root:example@localhost:27017")
MONGO_URI = raw_uri.strip()
client = MongoClient(MONGO_URI)
mongo_db = client["kirp"]

class PersistenceManager:
    @staticmethod
    def append_event(event_type: str, payload: Dict[str, Any], requires_approval: bool = False) -> str:
        # בדיקה אם האירוע כבר קיים (מניעת כפילויות וחיזוק חשיבות)
        # מחפש לפי סוג אירוע ותוכן המשימה/טקסט
        search_query = {"type": event_type}
        if "task" in payload: search_query["data.task"] = payload["task"]
        if "text" in payload: search_query["data.text"] = payload["text"]
        
        existing = mongo_db["events"].find_one(search_query)
        
        if existing:
            # אם קיים - מחזקים חשיבות ומעדכנים זמן
            new_importance = existing.get("importance", 1) + 1
            mongo_db["events"].update_one(
                {"id": existing["id"]},
                {"$set": {"importance": new_importance, "timestamp": datetime.datetime.utcnow().isoformat()}}
            )
            return existing["id"]

        # אם חדש - יוצרים רשומה רגילה
        event_id = str(uuid.uuid4())[:8]
        payload["importance"] = 1 # חשיבות התחלתית
        
        record = {
            "id": event_id,
            "type": event_type,
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "data": payload,
            "status": "pending_approval" if requires_approval else "completed",
            "metadata": {"source": "kirp_core"}
        }
        
        mongo_db["events"].insert_one(record)
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
