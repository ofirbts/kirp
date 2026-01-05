import asyncio
from app.services.memory_intelligence.summarize import decay_memory_strength
from app.storage.memory import fetch_relevant_memories

async def test_decay():
    print("🧪 בדיקת DECAY...")
    await decay_memory_strength()
    
    print("\n📊 זיכרונות חזקים (>0):")
    relevant = await fetch_relevant_memories(10)
    for m in relevant:
        print(f"  {m.content[:50]}... (strength: {m.strength})")
    
    print("\n✅ בדיקה הושלמה!")
    
asyncio.run(test_decay())
