import streamlit as st 
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timezone
import os
import streamlit.components.v1 as components
import time
import uuid
from pathlib import Path
# --- CONFIG & THEME ---
st.set_page_config(page_title="KIRP OS v7", page_icon="🧠", layout="wide")

API_URL = os.getenv("API_URL", "http://kirp-api:8000").rstrip('/')
EXTERNAL_URL = os.getenv("EXTERNAL_URL", "http://localhost:8501").rstrip('/')
CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")

def to_local(utc_dt):
    return utc_dt.replace(tzinfo=timezone.utc).astimezone(None) # None הופך לזמן המקומי של המחשב

def inject_custom_design():
    st.markdown("""
    <style>
    /* Main App Background */
    .stApp {
        background: radial-gradient(circle at top right, #111827, #020617);
        color: #e5e7eb;
        font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }
    /* צביעת טקסט כללי בלבד - מבלי לפגוע בתוך פקדים (Inputs) */
    .stApp {
        color: #e5e7eb;
    }

    /* הבטחת קריאות בתוך ה-Sidebar ובטקסטים חופשיים */
    [data-testid="stMarkdownContainer"] p, .stMarkdown {
        color: #e5e7eb !important;
    }

    /* תיקון ספציפי לתיבות טקסט ובחירה (שהטקסט בתוכן יהיה כהה על רקע לבן) */
    input, select, textarea, [data-baseweb="select"] * {
        color: #111827 !important; /* צבע כהה מאוד */
    }

    /* תיקון ה-Labels מעל תיבות הבחירה שיהיו לבנים על הרקע הכהה של האפליקציה */
    .stSelectbox label, .stTextInput label, .stMultiSelect label {
        color: #e5e7eb !important;
    }    
    /* החרגת ה-Tab labels והכפתורים שצריכים להישאר כהים */
    .stButton>button { color: #020617 !important; }
    
    /* תיקון צבע כותרות */
    h1, h2, h3, .kirp-title {
        color: #22d3ee !important;
    }
    
    /* עיצוב ה-Tabs שיהיו קריאים */
    button[data-baseweb="tab"] p {
        color: #e5e7eb !important;
    }
    /* Global headings */
    h1, h2, h3, h4 {
        font-weight: 700 !important;
        letter-spacing: 0.03em;
    }

    /* Top-level title */
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

    /* Sidebar */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #020617, #020617);
        border-right: 1px solid rgba(148, 163, 184, 0.25);
    }
    section[data-testid="stSidebar"] .css-1d391kg, 
    section[data-testid="stSidebar"] .css-1v3fvcr {
        color: #e5e7eb !important;
    }

/* Sidebar radio buttons */
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

    /* Metric cards – OS style */
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

    /* Status header bar */
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

    /* Insight cards */
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

    /* Logs panel */
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

    /* Buttons */
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

    /* Chat messages */
    .stChatMessage {
        background: rgba(15, 23, 42, 0.9) !important;
        border-radius: 14px !important;
        border: 1px solid rgba(148, 163, 184, 0.4) !important;
    }
    </style>
    """, unsafe_allow_html=True)

inject_custom_design()
# --- SESSION STATE ---
for key in ['authenticated', 'user_id', 'access_token', 'processed_codes', 'user_name']:
    if key not in st.session_state:
        if key == 'authenticated': st.session_state[key] = False
        elif key == 'processed_codes': st.session_state[key] = set()
        else: st.session_state[key] = None

# --- API HELPER ---
def kirp_api_call(method, endpoint, payload=None):
    headers = {}
    if "access_token" in st.session_state:
        headers["Authorization"] = f"Bearer {st.session_state.access_token}"
    
    url = f"{API_URL}{endpoint}"
    try:
        if method == 'POST':
            res = requests.post(url, json=payload, headers=headers, timeout=15)
        else:
            res = requests.get(url, headers=headers, timeout=10)
        
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
# --- 1) GOOGLE OAUTH CALLBACK HANDLING ---
query_params = st.query_params
if "code" in query_params and not st.session_state.authenticated:
    auth_code = query_params["code"]
    res = kirp_api_call("POST", "/auth/google/callback", {"code": auth_code})
    if res and res.status_code == 200:
        data = res.json()
        st.session_state.update({
            "authenticated": True,
            "access_token": data["access_token"],
            "user_id": data["user"]["user_id"],
            "user_name": data["user"]["full_name"]
        })
        st.query_params.clear()
        st.rerun()

# --- 2) LOGIN SCREEN ---
if not st.session_state.authenticated:
    col_a, col_b, col_c = st.columns([1, 2, 1])
    with col_b:
        st.markdown("<h1 style='text-align: center; color: #00ffcc;'>KIRP OS v7</h1>", unsafe_allow_html=True)
        
        tab_login, tab_reg = st.tabs(["🔒 Secure Entry", "✉️ New Identity"])
        
        with tab_login:
            u = st.text_input("Identity (Username)")
            p = st.text_input("Cipher (Password)", type="password")
            if st.button("Initialize Boot Sequence", use_container_width=True):
                res = kirp_api_call("POST", "/auth/login", {"username": u, "password": p})
                if res and res.status_code == 200:
                    d = res.json()
                    st.session_state.update({
                        "authenticated": True,
                        "access_token": d["access_token"],
                        "user_id": d["user"]["user_id"],
                        "user_name": d["user"]["full_name"]
                    })
                    st.rerun()
                else:
                    st.error("Access Denied")

        if CLIENT_ID:
            st.markdown("<p style='text-align: center; margin-top: 20px;'>OR</p>", unsafe_allow_html=True)
            redirect_uri = EXTERNAL_URL 
            google_url = (
                f"https://accounts.google.com/o/oauth2/v2/auth?"
                f"client_id={CLIENT_ID}&"
                f"response_type=code&"
                f"scope=openid%20email%20profile&"
                f"redirect_uri={redirect_uri}&"
                f"access_type=offline"
            )
            
            # שימוש ב-st.markdown עם HTML ישיר במקום components.html
            st.markdown(f"""
                <a href="{google_url}" target="_self" style="text-decoration:none;">
                    <div style="background:white; color:#444; padding:12px; border-radius:8px; text-align:center; font-weight:bold; cursor:pointer; border:1px solid #ddd; display:flex; align-items:center; justify-content:center;">
                        <img src="https://upload.wikimedia.org/wikipedia/commons/5/53/Google_%22G%22_Logo.svg" style="width:18px; margin-right:8px;">
                        Continue with Google Intelligence
                    </div>
                </a>
            """, unsafe_allow_html=True)

    st.stop()
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
            "🚦 Processes Monitor",
            "➕ Ingestion Hub",
            "🧬 Self-Improvement Engine",
            "🤖 Agent Factory",
            "📊 Pipeline",
            "📜 System Logs",
        ]
    )
    st.divider()
    if st.button("🔌 Terminal Session"):
        st.session_state.authenticated = False
        st.rerun()

if menu == "🏠 Dashboard":
    st.markdown("<div class='kirp-title'>KIRP Intelligence OS</div>", unsafe_allow_html=True)
    st.markdown("<div class='kirp-subtitle'>SYSTEM PULSE · KNOWLEDGE · AGENTS · INSIGHTS</div>", unsafe_allow_html=True)
    st.write("")

    res = kirp_api_call("GET", f"/dashboard/summary/{st.session_state.user_id}")
    if res and res.status_code == 200:
        data = res.json()
        metrics = data["metrics"]
        health = data["health"]

        st.markdown(f"""
        <div class="kirp-status-bar">
            <div class="kirp-status-left">
                📡 SYSTEM CORE: OPERATIONAL
            </div>
            <div class="kirp-status-right">
                <span>🟢 DB: {health['mongodb']['latency']}</span>
                <span>🔵 Vector: {health['vector_store']['latency']}</span>
                <span>🟣 LLM: {health['llm']['latency']}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Knowledge Items", metrics["knowledge_items"], "+12%")
        c2.metric("Active Agents", metrics["active_agents"], "Stable")
        c3.metric("New Insights", metrics["new_insights"], "Critical", delta_color="inverse")
        c4.metric("Active Jobs", metrics["active_jobs"], "In Progress")

        st.markdown("---")

        col_graph, col_insights = st.columns([2.2, 1])

        with col_graph:
            st.subheader("📈 Processing Activity (Last 7 Days)")
            chart_data = pd.DataFrame({
                'Time': pd.date_range(start=datetime.now(), periods=7, freq='D'),
                'Knowledge Items': [1, 2, 3, 4, 4, 4, 4]
            })
            fig = px.area(chart_data, x='Time', y='Knowledge Items', color_discrete_sequence=['#22d3ee'])
            fig.update_layout(
                template="plotly_dark",
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(15,23,42,0.8)',
                height=320,
                margin=dict(l=10, r=10, t=30, b=10)
            )
            st.plotly_chart(fig, use_container_width=True)

        with col_insights:
            st.subheader("💡 System Insights")
            st.markdown("""
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
            """, unsafe_allow_html=True)
            if st.button("🔁 Refresh Intelligence", use_container_width=True):
                st.toast("Re-scanning events and jobs for fresh insights...")

elif menu == "🧠 Knowledge Hub":
    st.markdown("<div class='kirp-title'>Intelligent Query</div>", unsafe_allow_html=True)
    st.markdown("<div class='kirp-subtitle'>HYBRID RAG · SEMANTIC SEARCH · CONTEXTUAL ANSWERS</div>", unsafe_allow_html=True)
    st.write("")

    query = st.chat_input("Ask anything about your knowledge universe...")

    if query:
        with st.status("🔍 Running hybrid semantic retrieval...", expanded=True) as status:
            start_time = datetime.now()

            res = kirp_api_call("POST", "/query", {
                "query": query,
                "user_id": st.session_state.user_id
            })

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


elif menu == "📡 Sources":
    st.title("Data Sources · Unified Knowledge Ingestion")

    res = kirp_api_call("GET", "/sources")
    if not res or res.status_code != 200:
        st.error("Unable to load sources from API")
        st.stop()

    sources = res.json()

    # סטטוס עליון
    col_a, col_b, col_c, col_d = st.columns(4)
    col_a.metric("Total Sources", len(sources))
    col_b.metric("Active", sum(1 for s in sources if s["active"]))
    col_c.metric("Total Items", sum(s["total_items"] for s in sources))
    col_d.metric("Errors", sum(1 for s in sources if s.get("error_count", 0) > 0))

    st.markdown("---")

    # כרטיסים דינמיים
    for src in sources:
        with st.container(border=True):
            st.subheader(src["name"])
            st.caption(f"Channel: {src['channel']} · Status: {'active' if src['active'] else 'paused'}")
            st.write(f"**Total Items:** {src['total_items']}")
            st.write(f"**Last Sync:** {src.get('last_sync', 'N/A')}")
            st.progress(0.8, text="Sync Health (static for now)")


elif menu == "🧩 Agents Network":
    st.title("Autonomous Agents · KIRP Neural Fleet")

    # --- Fetch agents from API ---
    res = kirp_api_call("GET", "/agents")
    if not res or res.status_code != 200:
        st.error("Unable to load agents from API")
        st.stop()

    agents = res.json()

    # --- Top metrics ---
    col_top1, col_top2, col_top3, col_top4 = st.columns(4)
    col_top1.metric("Total Agents", len(agents))
    col_top2.metric("Autonomous", sum(1 for a in agents if a["autonomous"]))
    col_top3.metric("Total Actions", sum(a["actions_count"] for a in agents))
    avg_sr = (
        sum(a["success_rate"] for a in agents) / len(agents)
        if agents else 0
    )
    col_top4.metric("Avg Success Rate", f"{avg_sr*100:.1f}%")

    st.markdown("---")

    # --- Agent cards ---
    cols = st.columns(2)
    for idx, ag in enumerate(agents):
        with cols[idx % 2]:
            with st.container(border=True):
                st.subheader(ag["name"])
                st.caption(f"{ag['type']} · ID: {ag['id']}")
                st.write(ag["description"])

                c1, c2, c3 = st.columns(3)
                c1.metric("Actions", ag["actions_count"])
                c2.metric("Success", f"{ag['success_rate']*100:.1f}%")
                c3.metric("Mode", "Autonomous" if ag["autonomous"] else "Manual")

                st.caption(f"Last run: {ag.get('last_run', 'N/A')}")

                if st.button(f"Run {ag['name']}", key=f"run_agent_{ag['id']}"):
                    st.info("Agent execution endpoint will be wired soon.")
    
    # --- Wisdom Board Agent ---
    st.markdown("---")
    st.subheader("🧭 Wisdom Board Agent")
    st.caption("סוכן שמייצר לוח תבונה יומי / שבועי / חודשי")

    period = st.selectbox("Planning Horizon", ["Daily", "Weekly", "Monthly"])
    focus = st.multiselect("Focus Areas", ["RAG Optimization", "Infra Reliability", "Product Thinking", "Learning & Research"])

    if st.button("Generate Wisdom Board", key="agent_wisdom_board"):
        st.success(f"Wisdom Board ({period}) generated (mock).")
        st.markdown("""
        - **Today:** Focus on stabilizing Docker builds and monitoring RAG latency  
        - **This Week:** Explore new RAG patterns from LangChain blog  
        - **This Month:** Design v2 of Sources & Agents orchestration
        """)

elif menu == "📈 Insights & Analytics":
    st.title("Insights & Analytics · Strategic Intelligence")

    # --- Fetch insights from API ---
    res = kirp_api_call("GET", "/insights")
    if not res or res.status_code != 200:
        st.error("Unable to load insights from API")
        st.stop()

    data = res.json()
    insights = data["items"]

    # --- Top metrics ---
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Insights", data["total"])
    col2.metric("New", data["new"])
    col3.metric("Acted On", data["acted_on"])
    col4.metric("Avg Confidence", f"{data['avg_confidence']*100:.1f}%")

    st.markdown("---")

    # --- Filters ---
    f_type = st.multiselect("Types", ["trend", "opportunity", "risk"], default=["trend", "opportunity", "risk"])
    f_status = st.multiselect("Status", ["new", "in_progress", "resolved"], default=["new", "in_progress", "resolved"])

    st.markdown("### Active Insights")

    # --- Render insights ---
    for ins in insights:
        if ins["type"] not in f_type:
            continue
        if ins["status"] not in f_status:
            continue

        color = {
            "trend": "#38bdf8",
            "opportunity": "#22c55e",
            "risk": "#ef4444"
        }.get(ins["type"], "#22d3ee")

        with st.container(border=True):
            st.markdown(
                f"<span style='color:{color}; font-weight:bold;'>{ins['type'].upper()}</span>",
                unsafe_allow_html=True
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

elif menu == "🚦 Processes Monitor":
    st.title("Processing Jobs · Flow & Reliability")

    # --- Fetch summary ---
    summary_res = kirp_api_call("GET", "/jobs/summary")
    jobs_res = kirp_api_call("GET", "/jobs/all")

    if not summary_res or summary_res.status_code != 200:
        st.error("Unable to load job summary")
        st.stop()

    if not jobs_res or jobs_res.status_code != 200:
        st.error("Unable to load job list")
        st.stop()

    summary = summary_res.json()
    jobs = jobs_res.json()

    # --- Top metrics ---
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Jobs", summary["total"])
    c2.metric("Completed", summary["done"])
    c3.metric("In Progress", summary["in_progress"])
    c4.metric("Failed", summary["failed"])

    st.markdown("---")

    # --- Search ---
    search = st.text_input("Search by Job ID / Source")

    # --- Job list ---
    for job in jobs:
        if search and search.lower() not in job["id"].lower() and search.lower() not in job["source"].lower():
            continue

        with st.expander(f"{job['status']} · Job {job['id']} · {job.get('source', 'Internal')}"):
            st.write(f"**Status:** {job['status']}")
            st.write(f"**Chunks:** {job.get('chunks_count', 'N/A')}")
            st.write(f"**Processing Time:** {job.get('processing_time_ms', 'N/A')} ms")
            st.write(f"**Updated:** {job.get('updated_at', 'N/A')}")

            # Progress bar
            pct = (
                1.0 if job["status"] == "DONE"
                else 0.6 if job["status"] in ("EMBEDDED", "CHUNKED")
                else 0.3
            )
            st.progress(pct)

            # Error message
            if job["status"] == "FAILED":
                st.error(job.get("error_message", "Unknown error"))
                if st.button(f"Retry {job['id']}", key=f"retry_{job['id']}"):
                    res_retry = kirp_api_call("POST", f"/jobs/{job['id']}/retry")
                    if res_retry and res_retry.status_code == 200:
                        st.success("Retry scheduled")
                        st.rerun()
                    else:
                        st.error("Retry failed")

            # Timeline (future)
            st.caption("Pipeline Timeline (future): RECEIVED → CHUNKED → EMBEDDED → STORED → DONE")

    st.markdown("---")

    # --- Optimization Suggestions ---
    st.subheader("🧠 Optimization Suggestions (Self-Improvement Hooks)")

    st.info("These suggestions will be generated by the Self-Improvement Engine based on job failures, latency, and patterns.")

    st.markdown("""
    - Reduce chunk size for Support Emails to **400 tokens** to reduce embedding failures  
    - Increase retry delay for Slack ingestion to **5 seconds**  
    - Enable semantic deduplication for Notion documents  
    """)

elif menu == "➕ Ingestion Hub":
    st.title("Ingestion Hub · Feed the Brain")

    st.markdown("בחר איך להזין מידע חדש למערכת:")

    tab_text, tab_file, tab_stream = st.tabs(["📝 Manual Text", "📁 JSON / Files", "🔌 Live Streams"])

    # --- Manual Text Ingestion ---
    with tab_text:
        st.subheader("Manual Knowledge Item")

        src = st.selectbox("Source", ["manual", "whatsapp", "slack", "email", "notion"])
        category = st.selectbox("Category", ["technical", "business", "support", "general"])
        title = st.text_input("Title")
        text = st.text_area("Content")

        if st.button("Ingest Item", use_container_width=True):
            if not text.strip():
                st.warning("Please enter some content before ingesting.")
            else:
                payload = {
                    "text": text,
                    "metadata": {
                        "source": src,
                        "category": category,
                        "title": title
                    }
                }
                res = kirp_api_call("POST", "/ingest", payload)
                if res and res.status_code == 200:
                    st.success("Item ingested successfully into the Knowledge Engine.")
                else:
                    st.error("Ingestion failed. Check API logs.")

    # --- JSON Batch Ingestion ---
    with tab_file:
        st.subheader("Import JSON / NDJSON")

        uploaded = st.file_uploader("Upload JSON / NDJSON file", type=["json", "ndjson"])

        if uploaded and st.button("Parse & Ingest Batch", use_container_width=True):
            try:
                lines = uploaded.read().decode("utf-8").splitlines()
                items = []
                import json
                for line in lines:
                    obj = json.loads(line)
                    items.append({
                        "text": obj.get("text", ""),
                        "metadata": obj.get("metadata", {})
                    })

                res = kirp_api_call("POST", "/ingest/batch", items)
                if res and res.status_code == 200:
                    st.success(f"Batch ingested successfully. Chunks added: {res.json().get('chunks_added')}")
                else:
                    st.error("Batch ingestion failed.")
            except Exception as e:
                st.error(f"Error parsing file: {e}")

    # --- Live Streams Registration ---
    with tab_stream:
        st.subheader("Connect Live Stream")
        st.write("חיבור זרימה קבועה מ-WhatsApp / Slack / Webhook.")

        stream_type = st.selectbox("Stream Type", ["WhatsApp Webhook", "Slack Events API", "Custom Webhook"])
        endpoint = st.text_input("Callback URL / Webhook Endpoint")

        if st.button("Register Stream", use_container_width=True):
            if not endpoint.strip():
                st.warning("Please enter a valid endpoint URL.")
            else:
                payload = {
                    "type": stream_type.replace(" ", "_").lower(),  # או מיפוי מסודר
                    "endpoint": endpoint,
                    "config": {},
                }
                res = kirp_api_call("POST", "/streams/register", payload)
                if res and res.status_code == 200:
                    st.success("Stream registered successfully.")
                else:
                    st.error("Failed to register stream.")

elif menu == "🧬 Self-Improvement Engine":
    st.title("Self-Improvement Engine · KIRP Optimizing Itself")

    # --- Fetch improvements from API ---
    imp_res = kirp_api_call("GET", "/improvements/pending")
    if not imp_res or imp_res.status_code != 200:
        st.error("Unable to load improvement proposals")
        st.stop()

    improvements = imp_res.json()

    # --- Top metrics ---
    col1, col2, col3 = st.columns(3)
    col1.metric("Pending Improvements", len(improvements))
    col2.metric("Learning Sources", 3)  # future API
    col3.metric("Applied Changes", 0)   # future API

    st.markdown("---")

    # --- Learning Sources (static for now, dynamic later) ---
    st.subheader("Learning Sources")
    col_a, col_b, col_c = st.columns(3)

    with col_a:
        st.markdown("**LangChain Blog**")
        st.caption("Type: blog · Status: active · Frequency: daily")
        st.write("Topics: LLMs, RAG, Agents")
        st.button("Scan Now", key="learn_langchain_scan")

    with col_b:
        st.markdown("**Pinecone Docs**")
        st.caption("Type: documentation · Status: active · Frequency: weekly")
        st.write("Topics: Vector DB, Embeddings, Search")
        st.button("Scan Now", key="learn_pinecone_scan")

    with col_c:
        st.markdown("**Arxiv cs.AI**")
        st.caption("Type: research_paper · Status: active · Frequency: daily")
        st.write("Topics: AI, ML, NLP, RAG")
        st.button("Scan Now", key="learn_arxiv_scan")

    st.markdown("---")
    st.subheader("Improvement Proposals")

    if not improvements:
        st.info("No pending improvements. The system is fully optimized.")
    else:
        for imp in improvements:
            with st.container(border=True):
                st.markdown(f"**Config Key:** `{imp['target_config_key']}` → `{imp['new_value']}`")
                st.caption(f"Impact: {imp['impact_level']} · Created: {imp['created_at']}")
                st.write(imp["reasoning"])

                col_apply, col_dismiss = st.columns(2)

                # Apply button
                if col_apply.button("Apply", key=f"apply_{imp['id']}"):
                    apply_res = kirp_api_call("POST", f"/improvements/{imp['id']}/apply")
                    if apply_res and apply_res.status_code == 200:
                        st.success("Improvement applied successfully")
                        st.rerun()
                    else:
                        st.error("Failed to apply improvement")

                # Dismiss button (future)
                if col_dismiss.button("Dismiss", key=f"dismiss_{imp['id']}"):
                    dismiss_res = kirp_api_call("POST", f"/improvements/{imp['id']}/dismiss")
                    if dismiss_res and dismiss_res.status_code == 200:
                        st.success("Improvement dismissed")
                        st.rerun()
                    else:
                        st.error("Failed to dismiss improvement")

elif menu == "🤖 Agent Factory":
    st.title("Agent Factory · Create Autonomous Intelligence Units")

    st.markdown("Design and deploy new AI agents into the KIRP Neural Fleet.")

    st.markdown("---")

    # --- Agent Definition Form ---
    with st.form("agent_creator_form"):
        st.subheader("🧬 Agent Identity")

        col1, col2 = st.columns(2)
        with col1:
            agent_name = st.text_input("Agent Name", placeholder="e.g., Data Harmonizer")
        with col2:
            agent_role = st.selectbox(
                "Agent Type",
                ["planner", "executor", "analyzer", "rag", "custom", "orchestrator"]
            )

        agent_description = st.text_area(
            "Agent Description",
            placeholder="Describe what this agent is supposed to do..."
        )

        st.markdown("---")
        st.subheader("🧠 Capabilities")

        capabilities = st.multiselect(
            "Select Capabilities",
            [
                "Notion Sync",
                "Web Scan",
                "Log Analysis",
                "Code Interpreter",
                "Memory Classification",
                "RAG Querying",
                "Event Monitoring",
                "Task Extraction",
                "Summarization",
                "Pattern Detection",
                "Anomaly Detection",
            ]
        )

        st.markdown("---")
        st.subheader("⚙️ Operational Mode")

        col3, col4 = st.columns(2)
        with col3:
            autonomous = st.selectbox("Autonomy Level", ["Manual", "Autonomous"])
        with col4:
            schedule = st.selectbox(
                "Execution Schedule",
                ["On-demand", "Hourly", "Daily", "Weekly", "Event-driven"]
            )

        st.markdown("---")

        submitted = st.form_submit_button("🚀 Deploy Agent")

    # --- Deployment Logic ---
    if submitted:
            if not agent_name.strip():
                st.error("Agent name is required.")
            else:
                payload = {
                    "name": agent_name,
                    "type": agent_role,
                    "description": agent_description,
                    "capabilities": capabilities,
                    "autonomous": autonomous == "Autonomous",
                    "schedule": schedule,
                    "user_id": st.session_state.user_id
                }
                
                with st.spinner(f"Deploying {agent_name} to the Neural Fleet..."):
                    res = kirp_api_call("POST", "/agents/create", payload)
                    if res and res.status_code == 200:
                        st.success(f"🚀 Agent '{agent_name}' has been successfully deployed and initialized.")
                        st.balloons()
                        time.sleep(2)
                        st.rerun()
                    else:
                        st.error("Deployment failed. Please check the System Logs for details.")

elif menu == "📊 Pipeline":
    st.title("Data Pipeline · Transformation & Enrichment")
    st.markdown("ניהול שלבי העיבוד של פריטי הידע (Chunking, Embedding, Linking).")

    # ויזואליזציה של ה-Pipeline
    st.info("Pipeline Workflow: Ingestion → Validation → Chunking → Embedding → Vector Storage")
    
    

    st.subheader("Configuration Control")
    col1, col2 = st.columns(2)
    with col1:
        chunk_size = st.slider("Chunk Size (Tokens)", 100, 2000, 500)
        chunk_overlap = st.slider("Chunk Overlap", 0, 500, 50)
    with col2:
        embedding_model = st.selectbox("Embedding Model", ["text-embedding-3-small", "text-embedding-3-large", "cohere-multilingual-v3"])
        vector_db = st.selectbox("Vector Target", ["Qdrant Vector Search", "Pinecone", "Milvus"])

    if st.button("Update Pipeline Settings", use_container_width=True):
        st.success("Pipeline configuration updated. New items will follow these rules.")
        
    st.markdown("<div class='kirp-title'>Processing Pipeline</div>", unsafe_allow_html=True)
    st.markdown("<div class='kirp-subtitle'>INGESTION · CHUNKING · EMBEDDING · STORAGE</div>", unsafe_allow_html=True)
    st.write("")

    # --- Fetch summary ---
    summary_res = kirp_api_call("GET", "/jobs/summary")
    jobs_res = kirp_api_call("GET", "/jobs/all")

    if not summary_res or summary_res.status_code != 200:
        st.error("Unable to load pipeline summary")
        st.stop()

    if not jobs_res or jobs_res.status_code != 200:
        st.error("Unable to load pipeline jobs")
        st.stop()

    summary = summary_res.json()
    jobs = jobs_res.json()

    # --- Top metrics ---
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Jobs", summary["total"])
    c2.metric("Completed", summary["done"])
    c3.metric("In Progress", summary["in_progress"])
    c4.metric("Failed", summary["failed"])

    st.markdown("---")

    # --- Search ---
    search = st.text_input("Search by Job ID / Source / Status")

    # --- Job Cards ---
    for job in jobs:
        if search and search.lower() not in job["id"].lower() and search.lower() not in job["source"].lower() and search.lower() not in job["status"].lower():
            continue

        with st.container(border=True):
            st.subheader(f"Job {job['id']}")
            st.caption(f"Source: {job.get('source', 'N/A')} · Status: {job['status']}")

            # --- Timeline Visualization ---
            st.markdown("### 🛠 Pipeline Stages")

            stages = ["RECEIVED", "CHUNKED", "EMBEDDED", "STORED", "DONE"]
            current_stage = job.get("status", "RECEIVED")

            try:
                stage_index = stages.index(current_stage) + 1
            except ValueError:
                stage_index = 1

            st.progress(stage_index / len(stages))

            cols = st.columns(len(stages))
            for i, stage in enumerate(stages):
                if i < stage_index:
                    cols[i].markdown(f"✅ **{stage}**")
                elif i == stage_index:
                    cols[i].markdown(f"🟡 **{stage}**")
                else:
                    cols[i].markdown(f"⚪ {stage}")

            st.markdown("---")

            # --- Job Details ---
            st.markdown("### 📄 Job Details")
            c1, c2, c3 = st.columns(3)
            c1.write(f"**Chunks:** {job.get('chunks_count', 'N/A')}")
            c2.write(f"**Processing Time:** {job.get('processing_time_ms', 'N/A')} ms")
            c3.write(f"**Updated:** {job.get('updated_at', 'N/A')}")

            # --- Actions: Explain + Retry ---
            col_left, col_right = st.columns(2)

            with col_left:
                if st.button(f"Explain {job['id']}", key=f"explain_{job['id']}"):
                    exp_res = kirp_api_call("GET", f"/jobs/{job['id']}/explain")
                    if exp_res and exp_res.status_code == 200:
                        exp = exp_res.json()
                        st.markdown("#### Pipeline Explanation")
                        st.write(f"**Source:** {exp.get('source')}")
                        st.write(f"**Status:** {exp.get('status')}")
                        st.write(f"**Chunks:** {exp.get('chunks_count')}")
                        st.write(f"**Processing Time:** {exp.get('processing_time_ms')} ms")
                        st.write(f"**Reason / Error:** {exp.get('reason')}")
                        st.write(f"**Stages:** {' → '.join(exp.get('pipeline_stages', []))}")
                    else:
                        st.error("Failed to explain pipeline")

            with col_right:
                if job["status"] == "FAILED":
                    if st.button(f"Retry {job['id']}", key=f"retry_{job['id']}"):
                        res_retry = kirp_api_call("POST", f"/jobs/{job['id']}/retry")
                        if res_retry and res_retry.status_code == 200:
                            st.success("Retry scheduled")
                            st.rerun()
                        else:
                            st.error("Retry failed")

    st.markdown("---")

    st.subheader("🧠 Optimization Suggestions (Self-Improvement Hooks)")
    st.info("These suggestions will be generated by the Self-Improvement Engine based on job failures, latency, and patterns.")

    st.markdown("""
    - Reduce chunk size for Support Emails to **400 tokens** to reduce embedding failures  
    - Increase retry delay for Slack ingestion to **5 seconds**  
    - Enable semantic deduplication for Notion documents  
    """)

    st.markdown("---")

    # --- Optimization Suggestions ---
    st.subheader("🧠 Optimization Suggestions (Self-Improvement Hooks)")
    st.info("These suggestions will be generated by the Self-Improvement Engine based on job failures, latency, and patterns.")

    st.markdown("""
    - Reduce chunk size for Support Emails to **400 tokens** to reduce embedding failures  
    - Increase retry delay for Slack ingestion to **5 seconds**  
    - Enable semantic deduplication for Notion documents  
    """)
           

elif menu == "📜 System Logs":
    st.markdown("<div class='kirp-title'>System Logs</div>", unsafe_allow_html=True)
    st.markdown("<div class='kirp-subtitle'>EVENTS · JOBS · QUERIES · AGENTS</div>", unsafe_allow_html=True)
    st.write("")

    log_res = kirp_api_call("GET", "/system/logs")
    if log_res and log_res.status_code == 200:
        logs = log_res.json()
        
        if logs:
            import pandas as pd
            # הפיכה ל-DataFrame
            df = pd.DataFrame(logs)
            
            # עיבוד התאריך להצגה נקייה (שעה:דקה:שנייה)
            df['timestamp'] = pd.to_datetime(df['timestamp']).dt.strftime('%H:%M:%S')
            
            # שינוי שמות עמודות להצגה יפה בטבלה
            df.columns = ['Time', 'Level', 'Message']
            
            # הצגת הטבלה בעיצוב רחב
            st.dataframe(
                df, 
                use_container_width=True, 
                hide_index=True,
                column_config={
                    "Level": st.column_config.TextColumn("Level", width="small"),
                    "Time": st.column_config.TextColumn("Time", width="small"),
                }
            )
        else:
            st.info("No logs found in the system.")

        st.write("")
        if st.button("🧠 Analyze Logs with KIRP Intelligence"):
            st.info("Intelligence Engine is scanning logs for risks, trends and opportunities...")

st.sidebar.caption(f"KIRP OS v7.0.1 | By Ofir Betesh | {datetime.now(timezone.utc).strftime('%H:%M')}")
