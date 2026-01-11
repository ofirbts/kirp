import streamlit as st
from app.core.tenant import TenantContext
from app.core.metrics import Metrics
from app.core.persistence import PersistenceManager
from app.agent.agent import agent

st.set_page_config(layout="wide")

st.markdown("""
## 🚀 KIRP Enterprise Control Plane
**Governed AI • Memory • Observability • Multi-Tenant**
""")

# ===== Sidebar =====
st.sidebar.markdown("## 🧩 Tenant Control")
tenant = st.sidebar.selectbox(
    "Active Tenant",
    ["default", "demo", "enterprise"],
    index=0
)
TenantContext.set(tenant)
st.sidebar.success(f"🟢 Active: {tenant}")

# ===== Metrics =====
metrics = Metrics().snapshot()

c1, c2, c3, c4 = st.columns(4)
c1.metric("🟢 System Health", "OK")
c2.metric("🧠 Queries", metrics.get("qps", 0))
c3.metric("📈 Drift", f"{metrics.get('drift', 0)}%")
c4.metric("💾 Memory (MB)", round(metrics.get("memory_mb", 0), 1))

# ===== Agent State =====
state = agent.dump_state()

st.markdown("### 🧠 Agent Summary")
a1, a2, a3 = st.columns(3)
a1.metric("Total Decisions", state["state"].get("total_queries", 0))
a2.metric("Last Answer", "✅" if state["state"].get("last_answer") else "—")
a3.metric("Suggestions", len(state["state"].get("last_suggestions", [])))

with st.expander("🔍 Raw Agent State"):
    st.json(state)

# ===== Events =====
st.markdown("### 📜 Recent Events")
events = PersistenceManager.tail(50)
with st.expander("Show events"):
    st.json(events)
