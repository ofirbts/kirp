import asyncio
import logging
import uuid
import time
from datetime import datetime, timezone
from app.core.persistence import PersistenceManager
from app.services.pipeline import ingest_text 
from app.models.schemas import KnowledgeItem

# הגדרת לוגר
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("KIRP-Worker")

async def autonomous_worker_loop():
    logger.info("🤖 KIRP Autonomous Worker Started - V7 Engine")
    
    while True:
        try:
            db = await PersistenceManager.get_db()
            
            # 1. שליפת אירועים שטרם עובדו (תומך בכל סוגי ה-Ingestion)
            query = {
                "event_type": {"$in": ["knowledge_add", "ingest", "document_uploaded", "knowledge_received"]}, 
                "processed": {"$ne": True}
            }
            recent_events = await db.events.find(query).to_list(50)
            
            if not recent_events:
                await asyncio.sleep(5)
                continue

            for event in recent_events:
                start_time = time.time()
                payload = event.get("data", {})
                event_id = event["_id"]
                
                # חילוץ נתונים בסיסיים
                text = payload.get("text") or payload.get("content")
                user_id = payload.get("user_id", "system")
                source = payload.get("source", "worker")
                job_id = payload.get("job_id", f"job_{uuid.uuid4().hex[:6]}")

                if not text:
                    logger.warning(f"⚠️ Event {event_id} has no text content. Skipping.")
                    await db.events.update_one({"_id": event_id}, {"$set": {"processed": True, "error": "No content"}})
                    continue

                try:
                    # 2. עדכון סטטוס Job ל-PROCESSING
                    await db.jobs.update_one(
                        {"id": job_id},
                        {"$set": {
                            "status": "PROCESSING", 
                            "updated_at": datetime.now(timezone.utc)
                        }},
                        upsert=True
                    )

                    # 3. הרצת ה-Pipeline ב-Thread (כי הוא סינכרוני ועושה קריאות ל-LLM)
                    # ה-Pipeline מחזיר classification, chunks ו-embeddings
                    logger.info(f"⚙️ Processing Job {job_id} for user {user_id}...")
                    
                    result = await asyncio.to_thread(
                        ingest_text, 
                        text=text, 
                        source=source,
                        metadata={"user_id": user_id, "event_id": str(event_id)}
                    )

                    # 4. יצירת אובייקט ידע (KnowledgeItem) ושמירה ב-MongoDB
                    # אנחנו שומרים את התוצאה המעובדת (כולל ה-memory_type שנקבע ב-Pipeline)
                    k_item = {
                        "id": str(uuid.uuid4()),
                        "user_id": user_id,
                        "source": source,
                        "text": text,
                        "category": result.get("memory_type", "general"),
                        "metadata": {
                            **payload.get("metadata", {}),
                            "pipeline_version": "v7",
                            "processed_at": datetime.now(timezone.utc).isoformat()
                        },
                        "created_at": datetime.now(timezone.utc)
                    }
                    
                    await db.knowledge.insert_one(k_item)

                    # 5. עדכון סופי ל-Job כ-DONE
                    processing_ms = int((time.time() - start_time) * 1000)
                    await db.jobs.update_one(
                        {"id": job_id},
                        {"$set": {
                            "status": "DONE", 
                            "processing_time_ms": processing_ms,
                            "updated_at": datetime.now(timezone.utc)
                        }}
                    )

                    # 6. סימון האירוע כעובד בהצלחה
                    await db.events.update_one({"_id": event_id}, {"$set": {"processed": True}})
                    logger.info(f"✅ Successfully processed Job {job_id} in {processing_ms}ms")

                except Exception as inner_e:
                    logger.error(f"❌ Error processing event {event_id}: {str(inner_e)}")
                    await db.jobs.update_one(
                        {"id": job_id},
                        {"$set": {"status": "FAILED", "error": str(inner_e)}}
                    )
                    # מסמנים כעובד גם אם נכשל כדי לא להיכנס ללופ אינסופי, אבל עם תיעוד שגיאה
                    await db.events.update_one({"_id": event_id}, {"$set": {"processed": True, "error": str(inner_e)}})
                async def run_scheduled_agents():
                    """סורק סוכנים שצריכים לרוץ עכשיו ומפעיל אותם"""
                    db = await PersistenceManager.get_db()
                    # מחפש סוכנים אוטונומיים (כאן אפשר להוסיף לוגיקה של זמנים/Schedule)
                    active_agents = await db.agents.find({"autonomous": True}).to_list(10)
                    
                    for ag_config in active_agents:
                        logger.info(f"🤖 Agent {ag_config['name']} is performing autonomous task...")
                        # כאן הסוכן יכול לבצע משימות סריקת לוגים או אופטימיזציה
                        # לדוגמה:
                        # await agent.process_task(task_description="Scan system logs for errors and suggest fixes")
        except Exception as e:
            logger.error(f"❌ Worker Critical Loop Error: {str(e)}")
        
        await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(autonomous_worker_loop())