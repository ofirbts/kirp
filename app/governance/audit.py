from app.core.persistence import PersistenceManager

class AuditTrail:
    def record(self, action, data):
        PersistenceManager.append_event("audit", {"action": action, "data": data})
