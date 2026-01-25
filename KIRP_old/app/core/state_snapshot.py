import pandas as pd
from collections import Counter
from app.core.persistence import PersistenceManager

class SystemStateSnapshot:
    """מנתח את מצב המערכת הנוכחי על בסיס אירועים וזיכרונות"""
    
    @staticmethod
    def get_active_concepts(limit=50):
        events = PersistenceManager.read_events(limit=limit)
        # שליפת תוכן מזיכרונות
        memories = [e['payload'].get('content', '') for e in events if e['type'] == 'knowledge_add']
        
        # ניתוח מילים בסיסי (בעתיד נחליף ב-LLM שיוציא Entities)
        words = " ".join(memories).split()
        common = Counter([w for w in words if len(w) > 3]).most_common(5)
        
        return [{"concept": word, "strength": count} for word, count in common]

    @staticmethod
    def get_system_health():
        events = PersistenceManager.read_events(limit=100)
        return {
            "total_events": len(events),
            "memories_count": len([e for e in events if e['type'] == 'knowledge_add']),
            "last_active": events[-1]['timestamp'] if events else "N/A"
        }