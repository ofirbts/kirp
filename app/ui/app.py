import sys, os
import json
import asyncio
import pandas as pd
import streamlit as st
from datetime import date, datetime

# ---------------------------------------------------------
# PYTHONPATH FIX
# ---------------------------------------------------------
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

# ---------------------------------------------------------
# MOCK EMBEDDINGS
# ---------------------------------------------------------
from app.rag import embedder

class EmbeddingsMock:
    def __call__(self, text):
        return [0.0] * 10

    def embed_documents(self, texts):
        return [[0.0] * 10 for _ in texts]

    def embed_query(self, text):
        return [0.0] * 10

embedder.get_embeddings = lambda: EmbeddingsMock()

# ---------------------------------------------------------
# MOCK VECTOR STORE
# ---------------------------------------------------------
from app.rag import vector_store

class VectorStoreMock:
    def similarity_search_with_score(self, query, k=5):
        return []

    @property
    def docstore(self):
        class DS:
            _dict = {}
        return DS()

vector_store._store = VectorStoreMock()
vector_store.get_vector_store = lambda: vector_store._store

# ---------------------------------------------------------
# MOCK LLM
# ---------------------------------------------------------
from app.llm import client as llm_client_module

class LLMClientMock:
    async def apredict(self, prompt: str) -> str:
        if "מה אני אוהב" in prompt:
            return "אתה אוהב תותים, טכנולוגיה עמוקה, ומערכות שמשלבות מוח וארגון כמו KIRP."
        return "אני במצב פיתוח – אבל אני מנתח את השאלה שלך ומחזיר תשובת דמו חכמה 🙂"

llm_client_module.get_llm = lambda: LLMClientMock()

# ---------------------------------------------------------
# IMPORT PERSISTENCE + AGENT INSTANCE
# ---------------------------------------------------------
from app.core.persistence import PersistenceManager
from app.agent.agent import agent  # instance קיים

# ---------------------------------------------------------
# PAGE CONFIG & STYLING
# ---------------------------------------------------------
st.set_page_config(
    page_title="KIRP OS | Intelligence",
    page_icon="🧠",
    layout="wide"
)

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&display=swap');
    
    .stApp {
        background: radial-gradient(circle at top, #0f172a 0, #020617 55%);
        color: #f1f5f9;
        font-family: 'Inter', sans-serif;
    }
    
    .block-container {
        padding-top: 2rem;
        padding-bottom: 3rem;
        max-width: 1200px;
    }

    h1, h2, h3, h4 {
        color: #e5e7eb !important;
    }
    
    .kirp-card {
        background: rgba(30, 41, 59, 0.85);
        backdrop-filter: blur(14px);
        border-radius: 20px;
        padding: 24px;
        border: 1px solid rgba(148, 163, 184, 0.35);
        box-shadow: 0 18px 40px rgba(15, 23, 42, 0.9);
        margin-bottom: 18px;
        transition: transform 0.15s ease, border 0.15s ease, box-shadow 0.15s ease;
    }
    
    .kirp-card:hover {
        transform: translateY(-2px);
        border: 1px solid rgba(56, 189, 248, 0.6);
        box-shadow: 0 22px 52px rgba(15, 23, 42, 1);
    }

    .status-badge {
        background: rgba(30, 64, 175, 0.25);
        color: #bfdbfe;
        padding: 4px 12px;
        border-radius: 999px;
        font-size: 0.75rem;
        border: 1px solid rgba(129, 140, 248, 0.6);
        display: inline-flex;
        align-items: center;
        gap: 6px;
    }

    .status-dot {
        height: 8px; width: 8px; background-color: #22c55e; border-radius: 50%;
        box-shadow: 0 0 12px #22c55e;
    }

    .chat-bubble {
        background: rgba(15, 23, 42, 0.95);
        border-left: 4px solid #38bdf8;
        padding: 15px;
        border-radius: 0 14px 14px 0;
        margin: 10px 0;
        font-size: 0.95rem;
    }

    .user-bubble {
        background: rgba(30, 64, 175, 0.5);
        border-right: 4px solid #38bdf8;
        padding: 10px 14px;
        border-radius: 14px 0 0 14px;
        margin: 6px 0;
        font-size: 0.9rem;
        text-align: right;
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 999px;
        padding-bottom: 6px;
        padding-top: 6px;
    }

    .stTabs [data-baseweb="tab"] p {
        font-weight: 600;
        font-size: 0.92rem;
    }

    input, textarea {
        background-color: #020617 !important;
        border: 1px solid #334155 !important;
        color: #f9fafb !important;
        border-radius: 10px !important;
    }

    .stButton button {
        border-radius: 999px;
        padding: 0.5rem 1.4rem;
        border: none;
        background: linear-gradient(135deg, #2563eb, #38bdf8);
        color: white;
        font-weight: 600;
        box-shadow: 0 10px 30px rgba(37,99,235,0.6);
    }
    .stButton button:hover {
        filter: brightness(1.07);
        transform: translateY(-1px);
    }

    .timeline-item {
        border-left: 2px solid rgba(148,163,184,0.7);
        margin-left: 8px;
        padding-left: 12px;
        margin-bottom: 12px;
        position: relative;
    }
    .timeline-item::before {
        content: "";
        position: absolute;
        left: -7px;
        top: 4px;
        height: 10px;
        width: 10px;
        border-radius: 999px;
        background: #38bdf8;
        box-shadow: 0 0 10px rgba(56,189,248,0.8);
    }
    .timeline-time {
        color: #9ca3af;
        font-size: 0.75rem;
    }
    .timeline-title {
        color: #e5e7eb;
        font-size: 0.9rem;
        font-weight: 500;
    }
    .timeline-meta {
        color: #94a3b8;
        font-size: 0.8rem;
    }
    </style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# HEADER SECTION
# ---------------------------------------------------------
header_col, stats_col = st.columns([2, 1])

with header_col:
    st.markdown("""
        <div style='margin-bottom: 20px;'>
            <h1 style='margin:0; font-weight:700; background: linear-gradient(90deg, #38bdf8, #818cf8); -webkit-background-clip: text; -webkit-text-fill-color: transparent;'>
                KIRP Intelligence System
            </h1>
            <p style='color: #94a3b8; font-size: 1.05rem;'>Personal OS for Deep Intentional Living</p>
        </div>
    """, unsafe_allow_html=True)

with stats_col:
    events_for_stats = PersistenceManager.read_events(limit=1000)
    task_count = len([e for e in events_for_stats if e['type'] == 'task_add'])
    memory_count = len([e for e in events_for_stats if e['type'] in ('knowledge_add', 'memory_add')])

    st.markdown(f"""
        <div style='display:flex; justify-content: flex-end; gap: 10px; margin-top: 10px; flex-wrap: wrap;'>
            <div class='status-badge'><div class='status-dot'></div> System Online</div>
            <div class='status-badge'>📋 {task_count} Tasks</div>
            <div class='status-badge'>🧠 {memory_count} Memories</div>
            <div class='status-badge'>⚡ 42ms Latency</div>
        </div>
    """, unsafe_allow_html=True)

# ---------------------------------------------------------
# MAIN NAVIGATION
# ---------------------------------------------------------
tabs = st.tabs(["💬 Intelligence", "🧠 Core Memory", "✅ Actions", "🌐 Network", "⚙️ Internal"])

# ---------------------------------------------------------
# TAB 1: INTELLIGENCE (CHAT)
# ---------------------------------------------------------
with tabs[0]:
    st.markdown('<div class="kirp-card">', unsafe_allow_html=True)
    st.subheader("Query the OS")

    col_chat_left, col_chat_right = st.columns([2, 1])

    with col_chat_left:
        user_q = st.text_area(
            "What's on your mind?",
            placeholder="e.g., 'Summary of my KIRP project status'...",
            label_visibility="collapsed"
        )
        run_intent = st.button("Execute Intent")

        if run_intent and user_q:
            with st.spinner("Analyzing patterns..."):
                res = asyncio.run(agent.run(user_q))
                st.markdown("### Decision & Response")
                st.markdown(f'<div class="user-bubble">{user_q}</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="chat-bubble">{res}</div>', unsafe_allow_html=True)

                with st.expander("🔍 Trace Reasoning"):
                    st.json({
                        "intent": "information_retrieval",
                        "confidence": 0.98,
                        "source": "vector_store_idx_01",
                        "notes": "Dev mode, using mocked embeddings & LLM."
                    })
        elif run_intent and not user_q:
            st.warning("Please enter a query first.")

    with col_chat_right:
        st.markdown("##### Recent Prompts (Demo)")
        demo_prompts = [
            "What are my top 3 priorities this week?",
            "Summarize my current KIRP project tasks.",
            "What do I usually say I enjoy doing?",
        ]
        for p in demo_prompts:
            st.markdown(f"<div class='user-bubble'>{p}</div>", unsafe_allow_html=True)

        st.markdown("<br/><small style='color:#94a3b8;'>Soon: real conversation history, pinned prompts, and smart suggestions.</small>", unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)

# ---------------------------------------------------------
# TAB 2: CORE MEMORY
# ---------------------------------------------------------
with tabs[1]:
    col_l, col_r = st.columns([1, 1])
    
    with col_l:
        st.markdown('<div class="kirp-card">', unsafe_allow_html=True)
        st.subheader("Ingest Knowledge")

        mem_input = st.text_area("Record a new insight:", height=150)
        source = st.selectbox("Source Type", ["UI", "Meeting", "Thought", "Reading"])
        if st.button("Commit to Long-Term Memory"):
            if mem_input.strip():
                PersistenceManager.append_event("knowledge_add", {"content": mem_input, "source": source})
                st.success("Hashed and Stored.")
            else:
                st.warning("Please enter some content before storing.")
        st.markdown('</div>', unsafe_allow_html=True)
        
    with col_r:
        st.markdown('<div class="kirp-card">', unsafe_allow_html=True)
        st.subheader("Recent Memory Timeline")

        raw_events = PersistenceManager.read_events(limit=50)
        mem_events = [e for e in raw_events if e['type'] in ('knowledge_add', 'memory_add')]
        mem_events = sorted(mem_events, key=lambda e: e['timestamp'], reverse=True)[:8]

        if mem_events:
            for e in mem_events:
                payload = e.get("payload", {})
                content = payload.get("content", "")[:120] + ("..." if len(payload.get("content", "")) > 120 else "")
                src = payload.get("source", "unknown")
                t = e["timestamp"].replace("T", " ")[:16]
                st.markdown(
                    f"""
                    <div class="timeline-item">
                      <div class="timeline-time">{t}</div>
                      <div class="timeline-title">{content}</div>
                      <div class="timeline-meta">Source: {src}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        else:
            st.info("No memory events yet – start by storing some insights.")

        st.markdown(
            "<small style='color:#94a3b8;'>Soon: clustering, tags, projects, and memory strength visualization.</small>",
            unsafe_allow_html=True,
        )

        st.markdown('</div>', unsafe_allow_html=True)

# ---------------------------------------------------------
# TAB 3: ACTIONS (TASKS)
# ---------------------------------------------------------
with tabs[2]:
    st.markdown('<div class="kirp-card">', unsafe_allow_html=True)
    st.subheader("Active Pipeline")

    raw_events = PersistenceManager.read_events(limit=200)
    tasks = [e for e in raw_events if e['type'] == 'task_add']

    col_t_left, col_t_right = st.columns([1.5, 1])

    with col_t_left:
        if tasks:
            df_data = []
            for t in tasks:
                p = t.get('payload', {})
                df_data.append({
                    "Time": t['timestamp'][:16],
                    "Task": p.get('text', 'N/A'),
                    "Due": p.get('due', 'N/A'),
                    "Category": p.get('category', 'General')
                })
            df = pd.DataFrame(df_data)
            st.dataframe(df, use_container_width=True)
        else:
            st.write("No active tasks found in the event bus.")

    with col_t_right:
        st.markdown("##### Task Load Overview")

        if tasks:
            by_category = {}
            for t in tasks:
                cat = t.get("payload", {}).get("category", "General")
                by_category[cat] = by_category.get(cat, 0) + 1
            cat_df = pd.DataFrame(
                {"Category": list(by_category.keys()), "Count": list(by_category.values())}
            ).set_index("Category")
            st.bar_chart(cat_df)
        else:
            st.info("No tasks to visualize yet.")

        st.markdown(
            "<small style='color:#94a3b8;'>Soon: today / tomorrow / week views, calendar sync, and priority levels.</small>",
            unsafe_allow_html=True,
        )

    st.markdown('</div>', unsafe_allow_html=True)

# ---------------------------------------------------------
# TAB 4: NETWORK (INTEGRATIONS)
# ---------------------------------------------------------
with tabs[3]:
    st.markdown('<div class="kirp-card">', unsafe_allow_html=True)
    st.subheader("Connected Surfaces")

    col_i1, col_i2, col_i3 = st.columns(3)

    with col_i1:
        st.markdown("##### 📧 Gmail")
        st.markdown("<span style='color:#22c55e; font-size:0.9rem;'>● Connected (Demo)</span>", unsafe_allow_html=True)
        st.markdown("<span style='color:#cbd5f5; font-size:0.85rem;'>Import important threads as memories and tasks.</span>", unsafe_allow_html=True)
        st.button("Check Gmail Link", key="gmail_check")

    with col_i2:
        st.markdown("##### 📆 Google Calendar")
        st.markdown("<span style='color:#22c55e; font-size:0.9rem;'>● Connected (Demo)</span>", unsafe_allow_html=True)
        st.markdown("<span style='color:#cbd5f5; font-size:0.85rem;'>Sync tasks into events and query your schedule.</span>", unsafe_allow_html=True)
        st.button("Check Calendar Link", key="cal_check")

    with col_i3:
        st.markdown("##### 💬 WhatsApp")
        st.markdown("<span style='color:#22c55e; font-size:0.9rem;'>● Connected (Demo)</span>", unsafe_allow_html=True)
        st.markdown("<span style='color:#cbd5f5; font-size:0.85rem;'>Talk to KIRP from your phone, store memories from chats.</span>", unsafe_allow_html=True)
        st.button("Check WhatsApp Link", key="wa_check")

    st.markdown(
        "<br/><small style='color:#94a3b8;'>Soon: OAuth setup, channel preferences, and routing rules for what becomes memory vs. tasks.</small>",
        unsafe_allow_html=True,
    )

    st.markdown('</div>', unsafe_allow_html=True)

# ---------------------------------------------------------
# TAB 5: INTERNAL (SYSTEM STATUS)
# ---------------------------------------------------------
with tabs[4]:
    st.subheader("Event Bus Registry")
    st.markdown('<div class="kirp-card">', unsafe_allow_html=True)
    st.write("Real-time system events (Persistence Layer):")

    last_events = PersistenceManager.read_events(limit=50)
    if last_events:
        table_rows = [{"id": e['id'][:8], "type": e['type'], "time": e['timestamp']} for e in last_events[-10:]]
        st.table(pd.DataFrame(table_rows))
    else:
        st.info("No events yet.")

    st.markdown(
        "<br/><small style='color:#94a3b8;'>Soon: error heatmaps, performance traces, and self-healing suggestions.</small>",
        unsafe_allow_html=True,
    )

    st.markdown('</div>', unsafe_allow_html=True)

# FOOTER
st.markdown(
    "<div style='text-align:center; margin-top:40px; color:#64748b;'>"
    "KIRP Intelligence | Deterministic Replay: Enabled | Version 2.1.0"
    "</div>",
    unsafe_allow_html=True,
)
