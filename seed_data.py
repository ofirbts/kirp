import sys
import os

# הוספת נתיב הפרויקט כדי שיוכל למצוא את app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__))))

import asyncio
from app.core.persistence import PersistenceManager

def seed_system():
    print("🚀 Starting Professional Seed Ingestion based on Ofir's Profile...")

    try:
        # 1. תובנות מקצועיות ואישיות (Knowledge Base - RAG)
        # מבוסס על ניסיון ניהולי וטכני 
        knowledge_items = [
            "אופיר בטש הוא מנהל פרויקטים מנוסה עם למעלה מ-10 שנות ניסיון בהובלת צוותים ותהליכים מורכבים[cite: 82].",
            "לאופיר רקע טכני עשיר הכולל בניית אתרים ועיצוב גרפי עבור ארגונים ולקוחות פרטיים[cite: 110].",
            "היעד המקצועי הנוכחי: הסבת כישורי הניהול והתקשורת הבינאישית לתחום פיתוח התוכנה.",
            "סגנון עבודה: אופיר מאמין במנהיגות שפועלת מהלב, ביצירתיות רבת-שכבות ובחיבור בין טכנולוגיה לערכים[cite: 13, 10].",
            "המערכת הנוכחית (KIRP OS) נבנית כדי לסייע בניהול משימות, זיכרון ארגוני ואופטימיזציה של תהליכי עבודה אישיים.",
            "אופיר בעל יכולת לימוד עצמית גבוהה מאוד וניסיון עשיר בעמידה מול קהל והעברת תכנים מורכבים[cite: 17, 97].",
            "ערכי ליבה: צמיחה מתוך למידה, התמדה, אחריות ומשפחתיות[cite: 50, 46, 27]."
        ]

        for item in knowledge_items:
            PersistenceManager.append_event("knowledge_add", {"text": item, "source": "Professional_Profile_Seed"})

        # 2. משימות פעילות (Action Pipeline)
        # משימות שמשלבות את פיתוח האפליקציה והקריירה
        tasks = [
            {"task": "אופטימיזציה של ה-Docker Image לצמצום זמן ה-Build בענן", "priority": "High"},
            {"task": "הוספת תמיכה בהעלאת קבצי PDF לזיכרון הסמנטי של KIRP", "priority": "Medium"},
            {"task": "סקירת טכנולוגיות חדשות בתחום ה-RAG לשיפור איכות התשובות", "priority": "High"},
            {"task": "עדכון קורות חיים עם הפרויקטים הטכנולוגיים האחרונים (KIRP OS)", "priority": "Medium"},
            {"task": "בניית מצגת דמו למערכת עבור שותפים פוטנציאליים", "priority": "Low"}
        ]

        for t in tasks:
            PersistenceManager.append_event("task_identified", t, requires_approval=True)

        print(f"✅ Seed completed successfully!")
            
    except Exception as e:
        print(f"❌ Error during seed: {e}")
        print("\n💡 וודא שביצעת 'docker-compose up -d mongodb' לפני ההרצה.")

if __name__ == "__main__":
    seed_system()