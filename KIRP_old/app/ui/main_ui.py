import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timezone
import os
import json
import streamlit.components.v1 as components
import time
import uuid
from pathlib import Path
from app.ui import api as kirp_api

# --- CONFIG & THEME ---
st.set_page_config(page_title="KIRP OS v7", page_icon="🧠", layout="wide")
if "last_refresh" not in st.session_state:
    st.session_state.last_refresh = time.time()

# כל 30 שניות נרענן נתונים
if time.time() - st.session_state.last_refresh > 30:
    st.session_state.last_refresh = time.time()
    st.rerun()

API_URL = os.getenv("API_URL", "http://kirp-api:8000").rstrip("/")
EXTERNAL_URL = os.getenv("EXTERNAL_URL", "http://localhost:8501").rstrip("/")
CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")


def render_stats():
    try:
        res = requests.get(f"{API_URL}/api/v1/stats", timeout=5)
        if res.status_code == 200:
            stats = res.json()
            jobs = stats.get("jobs", {})
            pending = jobs.get("pending", 0)
            processing = jobs.get("processing", 0)
            active_jobs = pending + processing

            c1, c2 = st.columns(2)
            c1.metric("Memory Units", stats.get("knowledge_items", 0))
            c2.metric("Active Jobs", active_jobs)
    except Exception:
        st.error("Stats service unavailable")


render_stats()


def to_local(utc_dt):
    return utc_dt.replace(tzinfo=timezone.utc).astimezone(
        None
    )  # None הופך לזמן המקומי של המחשב


def inject_custom_design():
    st.markdown(
        """
    <style>
    /* Main App Background */
    .stApp {
        background: radial-gradient(circle at top right, #111827, #020617);
        color: #e5e7eb;
        font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }
    .stApp {
        color: #e5e7eb;
    }
    [data-testid="stMarkdownContainer"] p, .stMarkdown {
        color: #e5e7eb !important;
    }
    input, select, textarea, [data-baseweb="select"] * {
        color: #111827 !important;
    }
    .stSelectbox label, .stTextInput label, .stMultiSelect label {
        color: #e5e7eb !important;
    }
    .stButton>button { color: #020617 !important; }
    h1, h2, h3, .kirp-title {
        color: #22d3ee !important;
    }
    button[data-baseweb="tab"] p {
        color: #e5e7eb !important;
    }
    h1, h2, h3, h4 {
        font-weight: 700 !important;
        letter-spacing: 0.03em;
    }
    .kirp-title {
        font-size: 2.2rem;
        font-weight: 800;
        background: linear-gradient(90deg, #22d3ee, #a855f7);
        -webkit-background-clip: text;
        color: transparent;
        margin-bottom: 0.3rem;
    }
    .kirp-subtitle {
        font-size: 0.9rem;
        opacity: 0.7;
        text-transform: uppercase;
        letter-spacing: 0.18em;
    }
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #020617, #020617);
        border-right: 1px solid rgba(148, 163, 184, 0.25);
    }
    section[data-testid="stSidebar"] .css-1d391kg,
    section[data-testid="stSidebar"] .css-1v3fvcr {
        color: #e5e7eb !important;
    }
    .stRadio > label {
        font-weight: 600;
        letter-spacing: 0.04em;
        padding: 8px 12px;
        border-radius: 8px;
        transition: background 0.2s ease;
    }
    .stRadio > label:hover {
        background: rgba(255, 255, 255, 0.05);
    }
    .stRadio > label[data-selected="true"] {
        background: linear-gradient(90deg, #22d3ee, #0ea5e9);
        color: #020617 !important;
    }
    div[data-testid="stMetric"] {
        background: radial-gradient(circle at top left, rgba(34, 211, 238, 0.08), rgba(15, 23, 42, 0.95));
        border-radius: 16px;
        border: 1px solid rgba(148, 163, 184, 0.35);
        padding: 18px 16px;
        box-shadow: 0 18px 45px rgba(15, 23, 42, 0.8);
        transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
    }
    div[data-testid="stMetric"]:hover {
        transform: translateY(-4px);
        border-color: #22d3ee;
        box-shadow: 0 24px 60px rgba(8, 47, 73, 0.9);
    }
    div[data-baseweb="select"] > div {
        background-color: #1f2937 !important;
        color: white !important;
    }
    .kirp-status-bar {
        background: linear-gradient(90deg, rgba(34, 197, 94, 0.08), rgba(34, 211, 238, 0.06));
        border-radius: 14px;
        border: 1px solid rgba(34, 197, 94, 0.35);
        padding: 12px 18px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 18px;
    }
    .kirp-status-left {
        font-weight: 600;
        color: #bbf7d0;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        font-size: 0.8rem;
    }
    .kirp-status-right span {
        font-size: 0.8rem;
        margin-left: 14px;
        opacity: 0.85;
    }
    .kirp-insight-card {
        background: radial-gradient(circle at top left, rgba(56, 189, 248, 0.12), rgba(15, 23, 42, 0.98));
        border-radius: 14px;
        border: 1px solid rgba(59, 130, 246, 0.4);
        padding: 14px 14px;
        margin-bottom: 10px;
        font-size: 0.9rem;
    }
    .kirp-insight-title {
        font-weight: 600;
        margin-bottom: 4px;
    }
    .kirp-insight-meta {
        font-size: 0.75rem;
        opacity: 0.7;
    }
    .kirp-log-panel {
        background: #020617;
        border-radius: 12px;
        border: 1px solid rgba(148, 163, 184, 0.4);
        padding: 14px;
        font-family: "JetBrains Mono", "Fira Code", monospace;
        font-size: 0.78rem;
        height: 420px;
        overflow-y: auto;
    }
    .stButton>button {
        border-radius: 999px;
        border: 1px solid rgba(56, 189, 248, 0.6);
        background: radial-gradient(circle at top left, #22d3ee, #0ea5e9);
        color: #020617;
        font-weight: 600;
        letter-spacing: 0.05em;
        text-transform: uppercase;
        font-size: 0.78rem;
        padding: 0.5rem 1.2rem;
        transition: all 0.2s ease;
    }
    .stButton>button:hover {
        box-shadow: 0 0 22px rgba(34, 211, 238, 0.7);
        transform: translateY(-1px) scale(1.01);
    }
    .stChatMessage {
        background: rgba(15, 23, 42, 0.9) !important;
        border-radius: 14px !important;
        border: 1px solid rgba(148, 163, 184, 0.4) !important;
    }
    </style>
    """,
        unsafe_allow_html=True,
    )


inject_custom_design()

# --- SESSION STATE ---
for key in ["authenticated", "user_id", "access_token", "processed_codes", "user_name"]:
    if key not in st.session_state:
        if key == "authenticated":
            st.session_state[key] = False
        elif key == "processed_codes":
            st.session_state[key] = set()
        else:
            st.session_state[key] = None


# --- API HELPER ---
def kirp_api_call(method, endpoint, payload=None):
    headers = {}
    if "access_token" in st.session_state and st.session_state.access_token:
        headers["Authorization"] = f"Bearer {st.session_state.access_token}"

    url = f"{API_URL}{endpoint}"
    try:
        if method == "POST":
            res = requests.post(url, json=payload, headers=headers, timeout=30)
        else:
            res = requests.get(url, headers=headers, timeout=60)

        if res.status_code == 401:
            st.session_state.authenticated = False
            st.rerun()
        return res
    except Exception as e:
        st.error(f"📡 API Connection Error: {e}")
        return None


# --- AUTH STATE INIT ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "processed_codes" not in st.session_state:
    st.session_state.processed_codes = set()

# --- AUTH LOGIC ---
query_params = st.query_params
if "code" in query_params and not st.session_state.authenticated:
    auth_code = query_params["code"]
    res = kirp_api_call("POST", "/auth/google/callback", {"code": auth_code})
    if res and res.status_code == 200:
        data = res.json()
        st.session_state.update(
            {
                "authenticated": True,
                "access_token": data["access_token"],
                "user_id": data["user"]["user_id"],
                "user_name": data["user"]["full_name"],
            }
        )
        st.query_params.clear()
        st.rerun()

# --- 2) LOGIN SCREEN ---
if not st.session_state.authenticated:
    col_a, col_b, col_c = st.columns([1, 2, 1])
    with col_b:
        st.markdown(
            "<h1 style='text-align: center; color: #00ffcc;'>KIRP OS v7</h1>",
            unsafe_allow_html=True,
        )

        tab_login, tab_reg = st.tabs(["🔒 Secure Entry", "✉️ New Identity"])

        with tab_reg:
            new_u = st.text_input("Choose Identity (Username)")
            new_n = st.text_input("Full Name")
            new_p = st.text_input("Choose Cipher (Password)", type="password")

            if st.button("Register New Identity", use_container_width=True):
                reg_payload = {
                    "username": new_u,
                    "password": new_p,
                    "full_name": new_n,
                }
                res = kirp_api_call("POST", "/auth/register", reg_payload)
                if res and res.status_code == 200:
                    st.success("Identity created! You can now login.")
                else:
                    st.error("Registration failed. Name might be taken.")

        with tab_login:
            u = st.text_input("Identity (Username)")
            p = st.text_input("Cipher (Password)", type="password")
            if st.button("Initialize Boot Sequence", use_container_width=True):
                res = kirp_api_call(
                    "POST", "/auth/login", {"username": u, "password": p}
                )
                if res and res.status_code == 200:
                    d = res.json()
                    st.session_state.update(
                        {
                            "authenticated": True,
                            "access_token": d["access_token"],
                            "user_id": d["user"]["user_id"],
                            "user_name": d["user"]["full_name"],
                        }
                    )
                    st.rerun()
                else:
                    st.error("Access Denied")

        if CLIENT_ID:
            st.markdown(
                "<p style='text-align: center; margin-top: 20px;'>OR</p>",
                unsafe_allow_html=True,
            )
            redirect_uri = EXTERNAL_URL
            google_url = (
                f"https://accounts.google.com/o/oauth2/v2/auth?"
                f"client_id={CLIENT_ID}&"
                f"response_type=code&"
                f"scope=openid%20email%20profile&"
                f"redirect_uri={redirect_uri}&"
                f"access_type=offline"
            )
            st.markdown(
                f"""
                <a href="{google_url}" target="_self" style="text-decoration:none;">
                    <div style="background-color: #4285F4; color: white; padding: 12px; border-radius: 5px; text-align: center; font-weight: bold; font-family: sans-serif; cursor: pointer; border: none; transition: 0.3s;">
                        Continue with Google Intelligence
                    </div>
                </a>
            """,
                unsafe_allow_html=True,
            )

    st.stop()

# בשלב הזה יש לנו user_id תקין
user_id = st.session_state.user_id

# --- SIDEBAR NAVIGATION ---
with st.sidebar:
    st.image("/app/app/ui/assets/kirp_logo.png", width=100)
    st.markdown(f"### Welcome, **{st.session_state.user_name}**")
    menu = st.radio(
        "System Modules",
        [
            "🏠 Dashboard",
            "🧠 Knowledge Hub",
            "📡 Sources",
            "🧩 Agents Network",
            "📈 Insights & Analytics",
            "🚦  Processes Monitor & Pipeline",
            "➕ Ingestion Hub",
            "🧬 Self-Improvement Engine",
            "🤖 Agent Factory",
            "📚 OS Wiki & Documentation",
            "📜 System Logs",
        ],
    )
    st.divider()
    if st.button("🔌 Terminal Session"):
        st.session_state.authenticated = False
        st.rerun()

# --- DASHBOARD ---
if menu == "🏠 Dashboard":
    st.markdown(
        "<div class='kirp-title'>KIRP Intelligence OS</div>", unsafe_allow_html=True
    )
    st.markdown(
        "<div class='kirp-subtitle'>SYSTEM PULSE · KNOWLEDGE · AGENTS · INSIGHTS</div>",
        unsafe_allow_html=True,
    )
    st.write("")

    def render_dashboard(data):
        metrics = data.get("metrics", {})

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Knowledge Items", metrics.get("knowledge_items", 0))
        col2.metric("Active Jobs", metrics.get("active_jobs", 0))
        col3.metric("New Today", metrics.get("new_today", 0))
        col4.metric("System Health", "100%", delta="Stable")

        st.markdown("### 💡 AI Strategic Insights")
        insights_res = kirp_api_call("GET", f"/insights/{st.session_state.user_id}")
        if insights_res and insights_res.status_code == 200:
            for ins in insights_res.json():
                with st.expander(f"{ins['type'].upper()}: {ins['title']}"):
                    st.write(ins["description"])
                    if st.button("Mark as Acted", key=ins["id"]):
                        kirp_api_call("POST", f"/insights/{ins['id']}/act")

    res = kirp_api_call("GET", f"/dashboard/summary/{st.session_state.user_id}")
    if res and res.status_code == 200:
        data = res.json()
        metrics = data.get("metrics", {})
        health = data.get("health", {})

        st.markdown(
            f"""
        <div class="kirp-status-bar">
            <div class="kirp-status-left">📡 SYSTEM CORE: OPERATIONAL</div>
            <div class="kirp-status-right">
                <span>🟢 DB: {health.get('mongodb', {}).get('latency', 'N/A')}</span>
                <span>🔵 Vector: {health.get('vector_store', {}).get('latency', 'N/A')}</span>
                <span>🟣 LLM: {health.get('llm', {}).get('latency', 'N/A')}</span>
            </div>
        </div>
        """,
            unsafe_allow_html=True,
        )

        c1, c2, c3, c4 = st.columns(4)
        c1.metric(
            "Memory Units",
            metrics.get("knowledge_items", 0),
            f"+{metrics.get('new_today', 0)}",
        )
        c2.metric("Active Agents", metrics.get("active_agents", 0))
        c3.metric("Neural Insights", metrics.get("new_insights", 0))
        c4.metric("Pending Tasks", metrics.get("active_jobs", 0))
        st.divider()

        # --- CHAT בתוך הדשבורד ---
        with st.container(border=True):
            st.subheader("💬 System Intelligence Chat")

            if "messages" not in st.session_state:
                st.session_state.messages = []

            for message in st.session_state.messages:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])

            user_query = st.chat_input(
                "Ask KIRP about your knowledge or system status..."
            )

            if user_query:
                st.session_state.messages.append(
                    {"role": "user", "content": user_query}
                )
                with st.chat_message("user"):
                    st.markdown(user_query)

                with st.chat_message("assistant"):
                    with st.spinner("🧠 Thinking..."):
                        payload = {
                            "query": user_query,
                            "user_id": st.session_state.user_id,
                            "stream": False,
                        }

                        chat_res = kirp_api_call("POST", "/query", payload)

                        if chat_res and chat_res.status_code == 200:
                            answer = chat_res.json().get(
                                "answer",
                                "I processed your request but have no text response.",
                            )
                            st.markdown(answer)
                            st.session_state.messages.append(
                                {"role": "assistant", "content": answer}
                            )
                        else:
                            error_msg = (
                                "❌ I'm having trouble accessing my intelligence core right now."
                            )
                            st.error(error_msg)

        st.markdown("---")

        st.markdown("### ⚡ Quick Access")
        q_col1, q_col2, q_col3 = st.columns(3)

        with q_col1:
            if st.button("📖 Read OS Documentation", use_container_width=True):
                st.info("Navigate to Wiki in the sidebar for full docs.")

        with q_col2:
            if st.button("🏗 View Data Schema", use_container_width=True):
                st.warning("The Notion Contract is defined in the Wiki module.")

        with q_col3:
            if st.button("🤖 Agent Status Report", use_container_width=True):
                st.toast("Generating full system report...")

        st.divider()

        col_graph, col_insights = st.columns([2.2, 1])

        with col_graph:
            st.subheader("📈 Processing Activity (Last 7 Days)")
            chart_data = pd.DataFrame(
                {
                    "Time": pd.date_range(start=datetime.now(), periods=7, freq="D"),
                    "Knowledge Items": [1, 2, 3, 4, 4, 4, 4],
                }
            )
            fig = px.area(
                chart_data,
                x="Time",
                y="Knowledge Items",
                color_discrete_sequence=["#22d3ee"],
            )
            fig.update_layout(
                template="plotly_dark",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(15,23,42,0.8)",
                height=320,
                margin=dict(l=10, r=10, t=30, b=10),
            )
            st.plotly_chart(fig, use_container_width=True)

        with col_insights:
            st.subheader("💡 System Insights")
            st.markdown(
                """
            <div class="kirp-insight-card">
                <div class="kirp-insight-title">Trend: RAG Optimization Interest</div>
                <div>Increased focus on retrieval quality and latency in recent activity.</div>
                <div class="kirp-insight-meta">Type: trend · Confidence: 0.89</div>
            </div>
            <div class="kirp-insight-card">
                <div class="kirp-insight-title">Risk: Docker Build Time</div>
                <div>Build time exceeds 5 minutes threshold on multiple runs.</div>
                <div class="kirp-insight-meta">Type: risk · Confidence: 0.92</div>
            </div>
            """,
                unsafe_allow_html=True,
            )
            if st.button("🔁 Refresh Intelligence", use_container_width=True):
                st.toast("Re-scanning events and jobs for fresh insights...")

# --- KNOWLEDGE HUB ---
elif menu == "🧠 Knowledge Hub":
    st.markdown("<div class='kirp-title'>Intelligent Query</div>", unsafe_allow_html=True)
    st.markdown("<div class='kirp-subtitle'>HYBRID RAG · SEMANTIC SEARCH · CONTEXTUAL ANSWERS</div>", unsafe_allow_html=True)
    st.write("")

    query = st.chat_input("Ask anything about your knowledge universe...")

    if query:
        with st.status("🔍 Running hybrid semantic retrieval...", expanded=True) as status:
            start_time = datetime.now()

            payload = {
                "query": query,
                "user_id": user_id,
                "stream": False,
            }
            res = kirp_api_call("POST", "/query", payload)

            if not res or res.status_code != 200:
                status.update(label="❌ Query failed", state="error")
                st.error("Query failed. Check API logs.")
                st.stop()

            data = res.json()
            answer = data.get("answer", "No answer returned.")

            end_time = datetime.now()
            latency_ms = int((end_time - start_time).total_seconds() * 1000)

            # --- Display answer ---
            st.chat_message("assistant", avatar="🧠").write(answer)

            # --- Metadata section ---
            st.markdown("---")
            st.subheader("📊 Query Metadata")

            col_a, col_b = st.columns(2)
            col_a.metric("Latency", f"{latency_ms} ms")
            col_b.metric("User", st.session_state.user_name)

            # --- Context section (future) ---
            st.markdown("---")
            st.subheader("📚 Retrieved Context (future)")

            st.info("Context snippets, sources, and confidence scores will appear here once retrieval_pipeline is integrated.")

            status.update(label="✅ Query resolved with contextual answer", state="complete")
# --- KNOWLEDGE HUB ---

            # --- Display answer ---
            st.chat_message("assistant", avatar="🧠").write(answer)

            # --- Metadata section ---
            st.markdown("---")
            st.subheader("📊 Query Metadata")

            col_a, col_b = st.columns(2)
            col_a.metric("Latency", f"{latency_ms} ms")
            col_b.metric("User", st.session_state.user_name)

            # --- Context section (future) ---
            st.markdown("---")
            st.subheader("📚 Retrieved Context (future)")

            st.info(
                "Context snippets, sources, and confidence scores will appear here once retrieval_pipeline is integrated."
            )

            status.update(
                label="✅ Query resolved with contextual answer", state="complete"
            )

# --- SOURCES ---
elif menu == "📡 Sources":
    st.title("Data Sources · Unified Knowledge Ingestion")

    res = kirp_api_call("GET", "/sources")
    if not res or res.status_code != 200:
        st.error("Unable to load sources from API")
        st.stop()

    sources = res.json()

    col_a, col_b, col_c, col_d = st.columns(4)
    col_a.metric("Total Sources", len(sources))
    col_b.metric("Active", sum(1 for s in sources if s["active"]))
    col_c.metric("Total Items", sum(s["total_items"] for s in sources))
    col_d.metric("Errors", sum(s.get("error_count", 0) > 0 for s in sources))

    st.markdown("---")

    for src in sources:
        with st.container(border=True):
            st.subheader(src["name"])
            st.caption(
                f"Channel: {src['channel']} · Status: {'active' if src['active'] else 'paused'}"
            )
            st.write(f"**Total Items:** {src['total_items']}")
            st.write(f"**Last Sync:** {src.get('last_sync', 'N/A')}")
            st.progress(0.8, text="Sync Health (static for now)")

# --- AGENTS NETWORK ---
elif menu == "🧩 Agents Network":
    st.title("Autonomous Agents · KIRP Neural Fleet")

    res = kirp_api_call("GET", "/agents")
    if not res or res.status_code != 200:
        st.error("Unable to load agents from API")
        st.stop()

    agents = res.json()

    col_top1, col_top2, col_top3, col_top4 = st.columns(4)
    col_top1.metric("Total Agents", len(agents))
    col_top2.metric("Autonomous", sum(1 for a in agents if a["autonomous"]))
    col_top3.metric("Total Actions", sum(a["actions_count"] for a in agents))
    avg_sr = sum(a["success_rate"] for a in agents) / len(agents) if agents else 0
    col_top4.metric("Avg Success Rate", f"{avg_sr*100:.1f}%")

    st.markdown("---")

    agents_res = kirp_api_call("GET", "/agents")
    if agents_res:
        agents = agents_res.json()
        cols = st.columns(2)
        for idx, ag in enumerate(agents):
            with cols[idx % 2]:
                with st.container(border=True):
                    st.subheader(ag["name"])
                    success_rate = ag.get("success_rate", 0) * 100
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Actions", ag.get("actions_count", 0))
                    c2.metric("Success", f"{success_rate:.1f}%")
                    c3.metric(
                        "Mode", "Autonomous" if ag.get("autonomous") else "Manual"
                    )
                st.caption(f"Last run: {ag.get('last_run', 'N/A')}")

                if st.button(f"Run {ag['name']}", key=f"run_agent_{ag['id']}"):
                    run_res = kirp_api_call(
                        "POST",
                        f"/agents/{ag['id']}/run",
                        payload={"task": "Run diagnostic", "user_id": user_id},
                    )
                    if run_res and run_res.status_code == 200:
                        st.success("Agent executed successfully.")
                    else:
                        st.error("Agent run failed.")

    st.markdown("---")
    st.subheader("🧭 Wisdom Board Agent")
    st.caption("סוכן שמייצר לוח תבונה יומי / שבועי / חודשי")

    period = st.selectbox("Planning Horizon", ["Daily", "Weekly", "Monthly"])
    focus = st.multiselect(
        "Focus Areas",
        ["RAG Optimization", "Infra Reliability", "Product Thinking", "Learning & Research"],
    )

    if st.button("Generate Wisdom Board", key="agent_wisdom_board"):
        st.success(f"Wisdom Board ({period}) generated (mock).")
        st.markdown(
            """
        - **Today:** Focus on stabilizing Docker builds and monitoring RAG latency  
        - **This Week:** Explore new RAG patterns from LangChain blog  
        - **This Month:** Design v2 of Sources & Agents orchestration
        """
        )

# --- INSIGHTS & ANALYTICS ---
elif menu == "📈 Insights & Analytics":
    st.title("Insights & Analytics · Strategic Intelligence")

    res = kirp_api_call("GET", "/insights")
    if not res or res.status_code != 200:
        st.error("Unable to load insights from API")
        st.stop()

    data = res.json()
    insights = data if isinstance(data, list) else data.get("items", [])

    total_insights = len(insights)
    new_count = sum(1 for i in insights if i.get("status") == "new")
    acted_on_count = sum(
        1 for i in insights if i.get("status") in ("resolved", "in_progress")
    )
    avg_conf = (
        sum(i.get("confidence", 0.0) for i in insights) / total_insights
        if total_insights > 0
        else 0.0
    )

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Insights", total_insights)
    col2.metric("New", new_count)
    col3.metric("Acted On", acted_on_count)
    col4.metric("Avg Confidence", f"{avg_conf*100:.1f}%")

    st.markdown("---")

    f_type = st.multiselect(
        "Types", ["trend", "opportunity", "risk"], default=["trend", "opportunity", "risk"]
    )
    f_status = st.multiselect(
        "Status",
        ["new", "in_progress", "resolved"],
        default=["new", "in_progress", "resolved"],
    )

    st.markdown("### Active Insights")

    for ins in insights:
        if ins["type"] not in f_type:
            continue
        if ins["status"] not in f_status:
            continue

        color = {
            "trend": "#38bdf8",
            "opportunity": "#22c55e",
            "risk": "#ef4444",
        }.get(ins["type"], "#22d3ee")

        with st.container(border=True):
            st.markdown(
                f"<span style='color:{color}; font-weight:bold;'>{ins['type'].upper()}</span>",
                unsafe_allow_html=True,
            )
            st.subheader(ins["title"])
            st.write(ins["description"])

            c1, c2, c3 = st.columns(3)
            c1.write(f"Confidence: **{ins['confidence']*100:.1f}%**")
            c2.write(f"Impact: **{ins.get('impact_score', 'N/A')}**")
            c3.write(f"Status: **{ins['status']}**")

            act1, act2 = st.columns(2)
            if act1.button("Mark as Acted", key=f"act_{ins['id']}"):
                st.info("Will call /insights/{id}/act (future endpoint).")
            if act2.button("Create Follow-up Task", key=f"task_{ins['id']}"):
                st.info("Task creation endpoint will be added later.")

# --- PROCESSES MONITOR & PIPELINE ---
elif menu == "🚦  Processes Monitor & Pipeline":
    st.markdown(
        "<div class='kirp-title'>Data Pipeline & Job Monitor</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<div class='kirp-subtitle'>INGESTION · CHUNKING · EMBEDDING · STORAGE</div>",
        unsafe_allow_html=True,
    )

    with st.expander("⚙️ Pipeline Configuration & Optimization", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            chunk_size = st.slider("Chunk Size (Tokens)", 100, 2000, 500)
            chunk_overlap = st.slider("Chunk Overlap", 0, 500, 50)
        with col2:
            emb_model = st.selectbox(
                "Embedding Model",
                ["text-embedding-3-small", "openai", "cohere-multilingual-v3"],
            )
            v_db = st.selectbox(
                "Vector Target", ["Qdrant Vector Search", "Pinecone", "Milvus"]
            )

        if st.button("Update Pipeline Settings", use_container_width=True):
            st.success("Configuration updated for new ingestion jobs.")

    st.info(
        "🧠 **AI Suggestion:** Based on recent failures, consider reducing chunk size for WhatsApp TXT files to 400."
    )

    summary_res = kirp_api_call("GET", "/jobs/summary")
    jobs_res = kirp_api_call("GET", "/jobs/all")

    if jobs_res and jobs_res.status_code == 200:
        summary = summary_res.json()
        jobs = jobs_res.json()

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Jobs", summary.get("total", 0))
        m2.metric("Completed", summary.get("done", 0))
        m3.metric("In Progress", summary.get("in_progress", 0))
        m4.metric("Failed", summary.get("failed", 0), delta_color="inverse")

        st.divider()
        search = st.text_input("🔍 Search by Job ID, Source or Status")

        for job in jobs:
            j_id = job.get("id") or str(job.get("_id", "unknown"))
            j_source = job.get("source", "Internal")
            j_status = job.get("status", "PENDING")

            if search and not any(
                search.lower() in str(val).lower()
                for val in [j_id, j_source, j_status]
            ):
                continue

            with st.container(border=True):
                c_head, c_status = st.columns([3, 1])
                c_head.subheader(f"Job: {j_id}")
                c_status.write(f"**{j_status}**")

                st.caption(
                    f"Source: {j_source} | Updated: {job.get('updated_at', 'N/A')}"
                )

                stages = ["RECEIVED", "CHUNKED", "EMBEDDED", "STORED", "DONE"]
                current_idx = stages.index(j_status) + 1 if j_status in stages else 1
                st.progress(current_idx / len(stages))

                col_exp, col_ret, col_empty = st.columns([1, 1, 3])
                if col_exp.button("Explain", key=f"exp_{j_id}"):
                    st.json(job)

                if j_status == "FAILED":
                    if col_ret.button("Retry", key=f"ret_{j_id}"):
                        kirp_api_call("POST", f"/jobs/{j_id}/retry")

# --- INGESTION HUB ---
elif menu == "➕ Ingestion Hub":
    st.markdown(
        "<div class='kirp-title'>Ingestion Hub</div>", unsafe_allow_html=True
    )
    st.markdown(
        "<div class='kirp-subtitle'>MANUAL INPUT · FILES · STREAMS</div>",
        unsafe_allow_html=True,
    )

    tab_text, tab_batch, tab_streams = st.tabs(
        ["✏️ Manual Text", "📂 Batch Ingest", "📡 Streams"]
    )

    # Manual text ingest – כאן אפשר להשתמש ב־kirp_api.ingest
    with tab_text:
        st.subheader("Manual Text Ingestion")
        text_input = st.text_area(
            "Drop any note, idea, or snippet to store in your knowledge base:"
        )
        if st.button("Ingest Text", use_container_width=True):
            if not text_input.strip():
                st.warning("Please enter some text first.")
            else:
                try:
                    resp = kirp_api.ingest(text_input, user_id=user_id)
                    st.success("Text ingested successfully.")
                    st.json(resp)
                except Exception as e:
                    st.error(f"Ingestion failed: {e}")

    # Batch ingest – נשאר עם kirp_api_call ל־/ingest/batch
    with tab_batch:
        st.subheader("Batch Ingestion (JSON Lines)")
        uploaded_file = st.file_uploader(
            "Upload JSONL file with items", type=["jsonl", "txt"]
        )
        if uploaded_file is not None:
            content = uploaded_file.read().decode("utf-8").strip().splitlines()
            items = []
            for line in content:
                try:
                    obj = json.loads(line)
                    items.append(obj)
                except Exception:
                    continue

            st.write(f"Parsed {len(items)} items.")
            if st.button("Send Batch to API", use_container_width=True):
                res = kirp_api_call("POST", "/ingest/batch", items)
                if res and res.status_code == 200:
                    st.success("Batch ingestion started.")
                    st.json(res.json())
                else:
                    st.error("Batch ingestion failed.")

    # Streams registration – נשאר עם kirp_api_call
    with tab_streams:
        st.subheader("Register New Stream")
        name = st.text_input("Stream Name")
        channel = st.selectbox("Channel", ["whatsapp", "email", "slack", "custom"])
        config = st.text_area("Config (JSON)", value="{}")

        if st.button("Register Stream", use_container_width=True):
            try:
                cfg = json.loads(config or "{}")
            except Exception as e:
                st.error(f"Invalid JSON: {e}")
            else:
                payload = {"name": name, "channel": channel, "config": cfg}
                res = kirp_api_call("POST", "/streams/register", payload)
                if res and res.status_code == 200:
                    st.success("Stream registered.")
                    st.json(res.json())
                else:
                    st.error("Stream registration failed.")

# --- SELF-IMPROVEMENT ENGINE ---
elif menu == "🧬 Self-Improvement Engine":
    st.markdown(
        "<div class='kirp-title'>Self-Improvement Engine</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<div class='kirp-subtitle'>AUTOMATED DIAGNOSIS · IMPROVEMENT SUGGESTIONS</div>",
        unsafe_allow_html=True,
    )

    res = kirp_api_call("GET", "/improvements")
    if not res or res.status_code != 200:
        st.error("Unable to load improvements from API")
        st.stop()

    improvements = res.json()

    for imp in improvements:
        with st.container(border=True):
            st.subheader(imp["title"])
            st.write(imp["description"])
            st.write(f"Impact: **{imp.get('impact', 'N/A')}**")
            st.write(f"Status: **{imp.get('status', 'pending')}**")

            c1, c2 = st.columns(2)
            if c1.button("Apply", key=f"apply_{imp['id']}"):
                apply_res = kirp_api_call(
                    "POST", f"/improvements/{imp['id']}/apply"
                )
                if apply_res and apply_res.status_code == 200:
                    st.success("Improvement applied.")
                else:
                    st.error("Failed to apply improvement.")
            if c2.button("Dismiss", key=f"dismiss_{imp['id']}"):
                dismiss_res = kirp_api_call(
                    "POST", f"/improvements/{imp['id']}/dismiss"
                )
                if dismiss_res and dismiss_res.status_code == 200:
                    st.info("Improvement dismissed.")
                else:
                    st.error("Failed to dismiss improvement.")

# --- AGENT FACTORY ---
elif menu == "🤖 Agent Factory":
    st.markdown(
        "<div class='kirp-title'>Agent Factory</div>", unsafe_allow_html=True
    )
    st.markdown(
        "<div class='kirp-subtitle'>DEFINE · CONFIGURE · DEPLOY AGENTS</div>",
        unsafe_allow_html=True,
    )

    name = st.text_input("Agent Name")
    role = st.text_area("Agent Role / System Prompt")
    autonomous = st.checkbox("Autonomous Mode", value=True)

    if st.button("Create Agent", use_container_width=True):
        payload = {
            "name": name,
            "role": role,
            "autonomous": autonomous,
            "owner_id": user_id,
        }
        res = kirp_api_call("POST", "/agents/create", payload)
        if res and res.status_code == 200:
            st.success("Agent created.")
            st.json(res.json())
        else:
            st.error("Failed to create agent.")

# --- OS WIKI & DOCUMENTATION ---
elif menu == "📚 OS Wiki & Documentation":
    st.markdown(
        "<div class='kirp-title'>OS Wiki & Documentation</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "Central place for contracts, schemas, and operating procedures.", unsafe_allow_html=False
    )

    res = kirp_api_call("GET", "/wiki")
    if res and res.status_code == 200:
        docs = res.json()
        for doc in docs:
            with st.expander(doc.get("title", "Untitled")):
                st.markdown(doc.get("content", ""))
    else:
        st.info("Wiki endpoint not implemented yet. Use Notion / external docs for now.")

# --- SYSTEM LOGS ---
elif menu == "📜 System Logs":
    st.markdown(
        "<div class='kirp-title'>System Logs</div>", unsafe_allow_html=True
    )
    st.markdown(
        "<div class='kirp-subtitle'>EVENTS · ERRORS · DIAGNOSTICS</div>",
        unsafe_allow_html=True,
    )

    level = st.selectbox("Log Level", ["INFO", "WARNING", "ERROR", "DEBUG"])
    limit = st.slider("Max Entries", 10, 500, 100)

    res = kirp_api_call("GET", f"/logs?level={level}&limit={limit}")
    if res and res.status_code == 200:
        logs = res.json()
        with st.container(border=True):
            st.markdown("#### Recent Logs")
            for entry in logs:
                ts = entry.get("timestamp", "")
                lvl = entry.get("level", "")
                msg = entry.get("message", "")
                st.text(f"[{ts}] [{lvl}] {msg}")
    else:
        st.info("Logs endpoint not implemented or unavailable.")
# --- FOOTER ---
st.sidebar.caption(f"KIRP OS v7.0.1 | By Ofir Betesh | {datetime.now(timezone.utc).strftime('%H:%M')}")
