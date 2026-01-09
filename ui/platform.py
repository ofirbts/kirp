import sys, os
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import streamlit as st
import pandas as pd

from app.observability.metrics import get_metrics
from app.research.benchmarks import BenchmarkSuite
from app.core.tenant import TenantContext
from app.rag.vector_store import debug_info
from app.agent.agent import agent

# הגדרות עמוד
st.set_page_config(
    page_title="KIRP Enterprise Dashboard",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Sidebar – שליטה גלובלית
st.sidebar.title("KIRP Control Center")

tenant = st.sidebar.text_input("Tenant", TenantContext.get())
TenantContext.set(tenant)
st.sidebar.write(f"Current tenant: {tenant}")

st.sidebar.markdown("---")
st.sidebar.subheader("Integrations (Coming Soon)")
st.sidebar.checkbox("Notion", value=True, disabled=True)
st.sidebar.checkbox("WhatsApp", value=True, disabled=True)
st.sidebar.checkbox("Slack", value=False, disabled=True)

st.sidebar.markdown("---")
st.sidebar.subheader("Health Summary")

metrics = get_metrics()
st.sidebar.metric("Uptime (sec)", round(metrics["uptime"], 1))
st.sidebar.metric("Memory (MB)", round(metrics["memory_mb"], 1))
st.sidebar.metric("QPS", metrics["qps"])
st.sidebar.metric("Drift", metrics["drift"])

st.title("KIRP Enterprise Dashboard")

tab_obs, tab_agent, tab_vectors, tab_bench, tab_integrations = st.tabs(
    [
        "Observability",
        "Agent State",
        "Vector Store",
        "Benchmarks",
        "Integrations",
    ]
)

# TAB 1 – Observability
with tab_obs:
    st.header("System Observability")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Uptime (sec)", round(metrics["uptime"], 2))
    col2.metric("Memory (MB)", round(metrics["memory_mb"], 2))
    col3.metric("QPS", metrics["qps"])
    col4.metric("Drift", metrics["drift"])

    st.subheader("Live Metrics Snapshot")
    chart_data = pd.DataFrame(
        {
            "uptime": [metrics["uptime"]],
            "memory": [metrics["memory_mb"]],
        }
    )
    st.line_chart(chart_data)

# TAB 2 – Agent State
with tab_agent:
    st.header("Agent State")

    try:
        state = agent.dump_state()
        st.subheader("Raw State")
        st.json(state)

        if "state" in state and isinstance(state["state"], dict):
            st.subheader("Key Metrics")
            s = state["state"]
            cols = st.columns(3)
            cols[0].metric("Total queries", s.get("total_queries", 0))
            cols[1].metric("Sessions", s.get("sessions_count", 0))
            cols[2].metric("Memories", s.get("memories_count", 0))
    except Exception as e:
        st.error(f"Failed to load agent state: {e}")

# TAB 3 – Vector Store
with tab_vectors:
    st.header("Vector Store Status")
    try:
        info = debug_info()
        col1, col2 = st.columns(2)
        col1.metric("Vectors in RAM", info.get("vectors_count_ram", 0))
        col2.metric("Disk index exists", info.get("disk_exists", False))

        st.subheader("Raw Debug Info")
        st.json(info)
    except Exception as e:
        st.error(f"Failed to load vector store info: {e}")

# TAB 4 – Benchmarks
with tab_bench:
    st.header("Benchmarks")

    bench = BenchmarkSuite()
    queries = ["test", "pricing", "memory"]

    st.subheader("Retrieval Quality")
    try:
        results = bench.retrieval_quality(queries)
        df = pd.DataFrame(results)
        st.table(df)
    except Exception as e:
        st.error(f"Benchmark failed: {e}")

# TAB 5 – Integrations (Notion / WhatsApp / etc.)
with tab_integrations:
    st.header("Integrations Overview")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Notion")
        st.write("Status: Connected (placeholder)")
        st.write("Planned:")
        st.markdown("- Sync pages as long-term knowledge")
        st.markdown("- Bi-directional task sync")
        st.markdown("- Agent can write summaries back to Notion")

    with col2:
        st.subheader("WhatsApp")
        st.write("Status: Connected (placeholder)")
        st.write("Planned:")
        st.markdown("- Ingest conversations as session memories")
        st.markdown("- Answer via bot connector")
        st.markdown("- Per-contact/session personalization")

    st.subheader("Future Integrations")
    st.write("Slack, Email, CRM, Analytics – all via plugin system.")
    
with tab_agent:
    st.subheader("Pending Approvals")
    st.write("Pulling from Notion…")
