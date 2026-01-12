import asyncio
import sys
import os
from datetime import datetime

# הוספת נתיב הפרויקט - חייב להיות לפני הייבוא של app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))

try:
    from app.core.persistence import PersistenceManager
    from app.core.metrics import metrics
    from app.agent.agent import agent
    from app.core.integrations import mongo_db, redis_client
    from app.services.notion import notion
    from app.integrations.whatsapp_gateway import get_whatsapp_gateway
except ImportError as e:
    print(f"❌ Critical Import Error: {e}")
    sys.exit(1)

async def run_test():
    print("🚀 Starting KIRP Enterprise Integration Test v3.0...")
    print(f"⏰ Execution Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("-" * 50)

    # 1. Infrastructure Layer: Mongo & Redis
    try:
        mongo_db.command('ping')
        print("✅ MongoDB: Connected & Responsive")
    except Exception as e:
        print(f"❌ MongoDB: Connection Failed ({e})")

    try:
        metrics.record_query()
        val = redis_client.get("metrics:total_queries")
        print(f"✅ Redis: Connected (Total System Queries: {val})")
    except Exception as e:
        print(f"❌ Redis: Connection Failed ({e})")

    # 2. Storage Layer: Persistence & Dual-Write Audit
    try:
        e_id = PersistenceManager.append_event("test_audit", {"status": "validating_storage"})
        events = PersistenceManager.get_all_events(limit=10)
        if any(e['id'] == e_id for e in events):
            print(f"✅ Persistence: Dual-Write Audit Passed (ID: {e_id})")
        else:
            print("❌ Persistence: Write inconsistency detected.")
    except Exception as e:
        print(f"❌ Persistence: Failed ({e})")

    # 3. Intelligence Layer: RAG & LLM Logic
    print("\n🧠 Testing Intelligence & RAG Pipeline...")
    try:
        test_query = "מי זה אופיר?"
        response = await agent.query(test_query)
        if response and "answer_text" in response:
            print(f"✅ LLM: Core Agent Responsive")
            print(f"💬 Sample Response: '{response['answer_text'][:50]}...'")
        else:
            print("❌ LLM: Agent returned empty response.")
    except Exception as e:
        print(f"❌ Intelligence: Failed ({e})")

    # 4. Governance Layer: Task Identification & Approval Hold
    print("\n⚖️ Testing Governance & Action Pipeline...")
    try:
        task_text = "תקבע לי פגישה עם דוקטור כהן"
        event_id = PersistenceManager.append_event(
            "task_identified", 
            {"task": task_text, "suggested_action": "calendar_sync"}, 
            requires_approval=True
        )
        
        pending = PersistenceManager.get_pending_approvals()
        if any(p['id'] == event_id for p in pending):
            print(f"✅ Governance: Task successfully intercepted & held (ID: {event_id})")
        else:
            print("❌ Governance: Task bypassed approval! (CRITICAL)")
    except Exception as e:
        print(f"❌ Governance Loop: Failed ({e})")

    # 5. Integration Layer: Notion & WhatsApp
    print("\n🌐 Testing External Integrations...")
    if notion.enabled():
        print("✅ Notion: Service Enabled (Connected to API)")
    else:
        print("⚠️ Notion: Service Disabled (Using Mock/Null)")

    try:
        wa = get_whatsapp_gateway()
        wa_res = wa.send_message("system_test", "KIRP Audit: All systems online.")
        if wa_res:
            print(f"✅ WhatsApp: Gateway initialized (Provider: {type(wa).__name__})")
    except Exception as e:
        print(f"❌ WhatsApp: Gateway Failed ({e})")

    # 6. Final Summary
    print("\n" + "=" * 50)
    m_snap = metrics.snapshot()
    print(f"🏁 Audit Finished.")
    print(f"📊 System Health: {m_snap.get('health', 'Unknown')}")
    print("=" * 50)

if __name__ == "__main__":
    asyncio.run(run_test())