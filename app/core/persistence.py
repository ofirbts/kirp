
import os
import uuid
import datetime
import logging
from typing import Any, Dict, List, Optional
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, PyMongoError
from passlib.context import CryptContext
from contextlib import contextmanager

logger = logging.getLogger(__name__)

# הצפנת סיסמאות
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# MongoDB connection - SINGLETON עם retry
_mongo_client = None
_mongo_db = None

def get_mongo_connection():
    """חיבור יציב עם retry + healthcheck"""
    global _mongo_client, _mongo_db
    
    if _mongo_db is not None:
        try:
            _mongo_client.admin.command('ping')
            return _mongo_db
        except:
            logger.warning("Mongo ping failed, reconnecting...")
    
    raw_uri = os.getenv("MONGO_URI", "mongodb://mongodb:27017").strip()
    db_name = os.getenv("MONGO_DB_NAME", "kirp").strip()
    
    if not raw_uri:
        logger.error("❌ MONGO_URI missing!")
        raise ValueError("MONGO_URI missing")
    
    for attempt in range(5):
        try:
            client = MongoClient(
                raw_uri, 
                connectTimeoutMS=5000, 
                serverSelectionTimeoutMS=5000,
                maxPoolSize=10,
                retryWrites=True
            )
            client.admin.command('ping')
            _mongo_client = client
            _mongo_db = client[db_name]
            logger.info(f"✅ MongoDB connected: {db_name} (attempt {attempt+1})")
            return _mongo_db
        except (ConnectionFailure, PyMongoError) as e:
            logger.warning(f"Mongo connect attempt {attempt+1} failed: {e}")
            if attempt == 4:
                raise
    
    raise ConnectionError("Failed to connect to MongoDB after 5 retries")

def get_db():
    """Thread-safe DB getter"""
    return get_mongo_connection()

def get_user(user_id_or_email: str) -> Optional[Dict[str, Any]]:
    """חיפוש משתמש לפי ID או email"""
    try:
        db = get_db()
        user = db["users"].find_one({
            "$or": [{"username": user_id_or_email}, {"email": user_id_or_email}]
        })
        if user:
            user["_id"] = str(user["_id"])
        return user
    except Exception as e:
        logger.error(f"Get user error [{user_id_or_email}]: {e}")
        return None
    

class PersistenceManager:
    """Pure static methods - NO INSTANCES NEEDED"""
    
    @staticmethod
    def get_user(user_id_or_email: str) -> Optional[Dict[str, Any]]:
        """חיפוש משתמש מלא לפי ID או email - CRITICAL FOR AUTH"""
        try:
            db = get_db()
            user = db["users"].find_one({
                "$or": [{"username": user_id_or_email}, {"email": user_id_or_email}]
            })
            if user:
                user["_id"] = str(user["_id"])
            return user
        except Exception as e:
            logger.error(f"Get user error [{user_id_or_email}]: {e}")
            return None
    
    @staticmethod
    def create_user(username: str, password: str, email: str = None) -> bool:
        try:
            db = get_db()
            if db["users"].find_one({"username": username}):
                logger.warning(f"User exists: {username}")
                return False
            
            hashed = pwd_context.hash(password[:72])
            db["users"].insert_one({
                "username": username, 
                "password": hashed, 
                "email": email,
                "auth_provider": "local",
                "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
            })
            logger.info(f"👤 Local user created: {username}")
            return True
        except Exception as e:
            logger.error(f"Create user error [{username}]: {e}")
            return False
    
    @staticmethod
    def create_google_user(email: str, full_name: str = None, avatar_url: str = None) -> bool:
        """Google users ללא סיסמה"""
        try:
            db = get_db()
            if db["users"].find_one({"email": email}):
                logger.info(f"👤 Google user exists: {email}")
                return True
            
            db["users"].insert_one({
                "username": email, 
                "email": email, 
                "full_name": full_name or email,
                "avatar_url": avatar_url, 
                "auth_provider": "google",
                "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
            })
            logger.info(f"👤 Google user created: {email}")
            return True
        except Exception as e:
            logger.error(f"Google user error [{email}]: {e}")
            return False
    
    @staticmethod
    def verify_user(username: str, password: str = None) -> Optional[Dict[str, Any]]:
        """מחזיר user מלא אם תקין, None אחרת"""
        try:
            db = get_db()
            user = db["users"].find_one({"username": username})
            
            if not user:
                return None
            
            if user.get("auth_provider") == "google":
                return user  # Google users no password check
            
            if password and pwd_context.verify(password, user["password"]):
                return user
            
            return None
        except Exception as e:
            logger.error(f"Verify user error [{username}]: {e}")
            return None
    
    @staticmethod
    def append_event(user_id: str, event_type: str, data: Dict) -> str:
        """Append event with guaranteed ID"""
        try:
            db = get_db()
            event_id = str(uuid.uuid4())[:8]
            db["events"].insert_one({
                "id": event_id,
                "user_id": user_id,
                "type": event_type,
                "data": data,
                "status": "active",
                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
            })
            return event_id
        except Exception as e:
            logger.error(f"Append event error [{user_id}][{event_type}]: {e}")
            return "error"
    
    @staticmethod
    def get_user_events(user_id: str, limit: int = 100) -> List[Dict]:
        try:
            db = get_db()
            return list(db["events"].find(
                {"user_id": user_id}, 
                {"_id": 0}
            ).sort("timestamp", -1).limit(limit))
        except Exception as e:
            logger.error(f"Get events error [{user_id}]: {e}")
            return []
    
    @staticmethod
    def get_pending_approvals(user_id: str) -> List[Dict]:
        try:
            db = get_db()
            return list(db["events"].find(
                {"user_id": user_id, "status": "pending_approval"}, 
                {"_id": 0}
            ).sort("timestamp", -1))
        except Exception as e:
            logger.error(f"Get approvals error [{user_id}]: {e}")
            return []
    
    @staticmethod
    def update_event_status(event_id: str, status: str) -> bool:
        try:
            db = get_db()
            result = db["events"].update_one(
                {"id": event_id}, 
                {"$set": {"status": status}}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Update event error [{event_id}]: {e}")
            return False

    @staticmethod
    def get_user(user_id_or_email: str) -> Optional[Dict[str, Any]]:
        """Wrapper סטטי ל-get_user"""
        return get_user(user_id_or_email)

