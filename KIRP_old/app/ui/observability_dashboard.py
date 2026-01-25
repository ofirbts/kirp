import streamlit as st
import pandas as pd
from app.core.persistence import PersistenceManager
from app.core.metrics import metrics
from app.services.notion import notion

st.set_page_config(layout="wide", page_title="KIRP Control Plane")

st.title("🛡️ KIRP Enterprise Dashboard")

# שורת מטריקות מה-Redis
m = metrics.snapshot()
c1, c2, c3, c4 = st.columns(4)
c1.metric("System Health", m["health"])
c2.metric("Total Queries", m["qps"])
c3.metric("Drift", f"{m['drift']}%")
c4.metric("Notion Status", "✅ Connected" if notion.enabled() else "❌ Disconnected")

st.divider()

# ניהול אישורים (Governance)
st.subheader("📑 Pending Approvals")
pending = PersistenceManager.get_pending_approvals()
if pending:
    for p in pending:
        col1, col2, col3 = st.columns([3, 1, 1])
        col1.write(f"**Task:** {p['data'].get('task')}")
        if col2.button("Approve", key=f"app_{p['id']}"):
            PersistenceManager.update_event_status(p['id'], "approved")
            st.rerun()
        if col3.button("Reject", key=f"rej_{p['id']}"):
            PersistenceManager.update_event_status(p['id'], "rejected")
            st.rerun()
else:
    st.success("No pending approvals. System is autonomous.")

st.divider()

# לוג אירועים מ-MongoDB
st.subheader("📜 Recent Events (Audit Trail)")
events = PersistenceManager.get_all_events(limit=20)
if events:
    st.table([{"Time": e["timestamp"], "Type": e["type"], "Status": e["status"]} for e in events])
