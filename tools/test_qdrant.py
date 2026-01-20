import asyncio
import os
from app.rag.vector_store import search_vectors, add_texts_with_metadata

async def run_health_check():
    print("🔍 Starting KIRP Vector Health Check...")
    
    # 1. בדיקת הזרקת נתונים
    test_text = "The quick brown fox jumps over the lazy dog"
    test_meta = {"source": "health_check", "category": "test"}
    
    print("📤 Testing data ingestion...")
    count = add_texts_with_metadata([test_text], [test_meta])
    if count > 0:
        print(f"✅ Successfully added {count} test document.")
    else:
        print("❌ Failed to add text.")
        return

    # 2. בדיקת חיפוש סמנטי
    print("🔎 Testing semantic search...")
    query = "Something about a fast fox"
    results = await search_vectors(query, k=1)
    
    if results and len(results) > 0:
        res = results[0]
        print(f"✅ Search successful!")
        print(f"   - Match: '{res['text'][:30]}...'")
        print(f"   - Score: {res['score']}")
        print(f"   - Metadata: {res['meta']}")
    else:
        print("❌ Search returned no results.")

if __name__ == "__main__":
    asyncio.run(run_health_check())