# app/scripts/seed_data.py
import sys
import os
import asyncio
from datetime import datetime, timezone

# הוספת נתיב הפרויקט
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from app.core.persistence import PersistenceManager

async def seed_system():
    print("🚀 Starting Professional Seed Ingestion based on Ofir's Profile...")

    try:
        # 1. תובנות מקצועיות ואישיות
        knowledge_items = [
            "אופיר בטש הוא מנהל פרויקטים מנוסה עם למעלה מ-10 שנות ניסיון בהובלת צוותים ותהליכים מורכבים.",
            "לאופיר רקע טכני עשיר הכולל בניית אתרים ועיצוב גרפי עבור ארגונים ולקוחות פרטיים.",
            "היעד המקצועי הנוכחי: הסבת כישורי הניהול והתקשורת הבינאישית לתחום פיתוח התוכנה.",
            "סגנון עבודה: אופיר מאמין במנהיגות שפועלת מהלב, ביצירתיות רבת-שכבות ובחיבור בין טכנולוגיה לערכים.",
            "המערכת הנוכחית (KIRP OS) נבנית כדי לסייע בניהול משימות, זיכרון ארגוני ואופטימיזציה של תהליכי עבודה אישיים.",
            "אופיר בעל יכולת לימוד עצמית גבוהה מאוד וניסיון עשיר בעמידה מול קהל והעברת תכנים מורכבים.",
            "ערכי ליבה: צמיחה מתוך למידה, התמדה, אחריות ומשפחתיות.",
        ]

        print(f"📥 Injecting {len(knowledge_items)} knowledge items...")
        for item in knowledge_items:
            await PersistenceManager.save_event("knowledge_add", {
                "text": item,
                "source": "Professional_Profile_Seed",
                "created_at": datetime.now(timezone.utc).isoformat(),
            })

        # 2. משימות פעילות
        tasks = [
            {"task": "אופטימיזציה של ה-Docker Image לצמצום זמן ה-Build בענן", "priority": "High"},
            {"task": "הוספת תמיכה בהעלאת קבצי PDF לזיכרון הסמנטי של KIRP", "priority": "Medium"},
            {"task": "סקירת טכנולוגיות חדשות בתחום ה-RAG לשיפור איכות התשובות", "priority": "High"},
            {"task": "עדכון קורות חיים עם הפרויקטים הטכנולוגיים האחרונים (KIRP OS)", "priority": "Medium"},
            {"task": "בניית מצגת דמו למערכת עבור שותפים פוטנציאליים", "priority": "Low"},
        ]

        print(f"📝 Injecting {len(tasks)} tasks...")
        for t in tasks:
            await PersistenceManager.save_event("task_identified", {
                **t,
                "created_at": datetime.now(timezone.utc).isoformat(),
            })

        # 3. Seed ל־Improvements (כדי שיהיה מה לראות ב־Self‑Improvement Engine)
        improvements = [
            {
                "target_config_key": "rag.chunk_size",
                "new_value": 400,
                "reasoning": "הקטנת גודל הצ'אנק תשפר דיוק ותפחית כשלי embedding במסמכים ארוכים.",
                "impact_level": "high",
            },
            {
                "target_config_key": "pipeline.retry_delay_seconds",
                "new_value": 5,
                "reasoning": "הגדלת זמן ההמתנה בין ניסיונות תקטין עומס על שירותי צד ג'.",
                "impact_level": "medium",
            },
            {
                "target_config_key": "ingest.semantic_dedup.enabled",
                "new_value": True,
                "reasoning": "הפעלת dedup סמנטי תמנע כפילויות בזיכרון ותשפר ביצועים.",
                "impact_level": "high",
            },
        ]

        print(f"🧠 Injecting {len(improvements)} improvement proposals...")
        db = await PersistenceManager.get_db()
        now = datetime.now(timezone.utc)
        for imp in improvements:
            imp_doc = {
                **imp,
                "applied": False,
                "created_at": now,
                "applied_at": None,
            }
            await db.improvements.insert_one(imp_doc)

        print("✅ Seed completed successfully!")

    except Exception as e:
        print(f"❌ Error during seed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(seed_system())
