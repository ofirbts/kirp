# test_qdrant_health.py
import asyncio
import os
import sys
from pathlib import Path

# הוספת נתיב הפרויקט כדי שה-imports יעבדו
sys.path.append(str(Path(__file__).parent))

from app.rag.vector_store import search_vectors, add_texts_with_metadata

async def health_check():
    print("🧪 Starting Vector Store Health Check...")
    
    # 1. בדיקת כתיבה
    test_text = "AI is changing the way we process memory and knowledge."
    test_meta = {"id": "health-1", "source": "test-suite"}
    
    print("📡 Testing: Adding text to Qdrant...")
    added = add_texts_with_metadata([test_text], [test_meta])
    print(f"✅ Added {added} items.")

    # 2. בדיקת קריאה (Search)
    print("🔍 Testing: Semantic Search...")
    # נחכה רגע ש-Qdrant יאנדקס
    await asyncio.sleep(1) 
    
    results = await search_vectors("knowledge processing", k=1)
    
    if results:
        res = results[0]
        print("✅ SUCCESS! Qdrant responded.")
        print(f"📍 Match: {res['text'][:50]}...")
        print(f"📊 Score: {res['score']}")
        print(f"🏷️ Metadata: {res['meta']}")
        
        if res['score'] < 0.1:
            print("⚠️ Warning: Score is very low. Check embedding model.")
    else:
        print("❌ FAILURE: No results returned. Check Qdrant logs.")

if __name__ == "__main__":
    asyncio.run(health_check())