import os
from dotenv import load_dotenv
from app.services.notion import notion

load_dotenv()

def test():
    print("🚀 מנסה לשלוח משימת בדיקה ל-Notion...")
    result = notion.create_task_page(
        title="בדיקת מערכת KIRP",
        trace_id="test-123",
        source="Terminal Test",
        confidence=0.99
    )
    print(f"📊 תוצאה: {result}")

if __name__ == "__main__":
    test()