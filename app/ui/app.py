import sys, os
import asyncio
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

# הוספת נתיב הפרויקט
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from app.agent.agent import agent
from app.core.persistence import PersistenceManager
from app.core.metrics import metrics
from app.services.notion import notion 
from app.integrations.whatsapp_gateway import get_whatsapp_gateway

# אתחול שער הווטסאפ
wa_gateway = get_whatsapp_gateway()

# הגדרות דף
st.set_page_config(page_title="KIRP Intelligence OS", page_icon="🧠", layout="wide")

# --- CUSTOM CSS (המראה המקצועי) ---
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; }
    .metric-card { background: #1e2130; padding: 20px; border-radius: 12px; border: 1px solid #3d4b5c; text-align: center; }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] { background-color: #1e2130; border-radius: 4px 4px 0 0; padding: 10px 20px; }
    .footer { position: fixed; bottom: 10px; right: 10px; color: #5c6370; font-size: 12px; }
    .status-online { color: #00ff00; font-weight: bold; }
    .recent-activity-item { font-size: 13px; border-bottom: 1px solid #2d3139; padding: 5px 0; }
    </style>
""", unsafe_allow_html=True)

# --- DATA FETCHING (נתונים בזמן אמת) ---
all_events = PersistenceManager.get_all_events(limit=50)
m_stats = metrics.snapshot()
pending_tasks = PersistenceManager.get_pending_approvals()
memories = [e for e in all_events if "knowledge" in e.get('type', '') or "memory" in e.get('type', '')]

# --- SIDEBAR (החזרת הקיצורים והפעילות האחרונה) ---
with st.sidebar:
    st.header("🧠 Smart Shortcuts")
    suggestions = ["מה המשימות הפתוחות שלי?", "תסכם לי את הזיכרונות מהשבוע", "מה אני צריך להכין לשבת?"]
    for suggest in suggestions:
        if st.button(f"🔍 {suggest}", use_container_width=True):
            if "messages" not in st.session_state: st.session_state.messages = []
            st.session_state.messages.append({"role": "user", "content": suggest})
            # סימולציה של שליחת שאלה
            res = asyncio.run(agent.query(suggest))
            st.session_state.messages.append({"role": "assistant", "content": res['answer_text']})
            st.rerun()
    
    st.divider()
    st.subheader("Recent Activity")
    for e in all_events[:12]:
        time_str = e.get('timestamp', '').split('T')[-1][:5]
        icon = "⚡" if "decision" in e['type'] else "📝" if "task" in e['type'] else "🧠"
        st.markdown(f"<div class='recent-activity-item'><b>{time_str}</b> {icon} {e.get('type')}</div>", unsafe_allow_html=True)

# --- HEADER & METRICS ---
st.title("🧠 KIRP Intelligence System")
st.caption("Personal OS for Deep Intentional Living | v2.2.0 Enterprise")

m1, m2, m3, m4 = st.columns(4)
with m1:
    st.markdown(f'<div class="metric-card">System Status<br><h2 style="color:#00ff00">Online</h2><small>⚡ {m_stats.get("latency", "42")}ms</small></div>', unsafe_allow_html=True)
with m2:
    st.markdown(f'<div class="metric-card">Tasks<br><h2>{len(pending_tasks)} Active</h2><small>📋 Pending Approval</small></div>', unsafe_allow_html=True)
with m3:
    st.markdown(f'<div class="metric-card">Memories<br><h2>{len(memories)} Stored</h2><small>🧠 Core Vault</small></div>', unsafe_allow_html=True)
with m4:
    st.markdown(f'<div class="metric-card">Version<br><h2>2.2.0</h2><small>🟢 Stable Branch</small></div>', unsafe_allow_html=True)

st.divider()

# --- MAIN NAVIGATION ---
tab_chat, tab_vault, tab_actions, tab_network, tab_internal = st.tabs([
    "💬 Intelligence", "🧠 Core Memory", "✅ Actions", "🌐 Network", "⚙️ Internal"
])

# --- TAB 1: INTELLIGENCE ---
with tab_chat:
    if "messages" not in st.session_state: st.session_state.messages = []
    for m in st.session_state.messages:
        with st.chat_message(m["role"]): st.markdown(m["content"])

    if prompt := st.chat_input("What's on your mind?"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(prompt)
        with st.spinner("🧠 Thinking..."):
            res = asyncio.run(agent.query(prompt))
            st.session_state.messages.append({"role": "assistant", "content": res['answer_text']})
            if any(word in prompt.lower() for word in ["תזכיר", "צריך", "לקנות", "תקבע"]):
                st.toast("New task identified!", icon="📲")
        st.rerun()

# --- TAB 2: CORE MEMORY (החזרת ה-Ingest) ---
with tab_vault:
    st.subheader("🧠 Knowledge Ingest")
    col_in, col_pre = st.columns([2, 1])
    with col_in:
        text_input = st.text_area("Record a new insight:", placeholder="Type something important...", height=150)
    with col_pre:
        st.write("🔍 **Smart Detection**")
        if text_input:
            source_guess = "Web/Link" if "http" in text_input else "UI"
            st.success(f"Source: **{source_guess}**")
            if st.button("Store in Vault", use_container_width=True):
                PersistenceManager.append_event("knowledge_add", {"text": text_input, "source": source_guess})
                st.success("Memory archived!")
                st.rerun()
        else:
            st.info("Waiting for input...")

# --- TAB 3: ACTIONS ---
with tab_actions:
    st.subheader("📋 Task Pipeline")
    if not pending_tasks:
        st.success("All caught up!")
    else:
        selected_ids = st.multiselect("Select for Bulk Approve:", [t['id'] for t in pending_tasks])
        if st.button("✅ Bulk Approve") and selected_ids:
            for eid in selected_ids:
                task_data = next(t for t in pending_tasks if t['id'] == eid)
                if notion.enabled():
                    notion.create_task(title=task_data['data'].get('task', 'New Task'), trace_id=eid)
                PersistenceManager.update_event_status(eid, "approved")
            st.rerun()

        st.divider()
        for task in pending_tasks:
            with st.expander(f"📌 {task['data'].get('task', 'New Task')}"):
                st.json(task['data'])
                c1, c2 = st.columns(2)
                if c1.button("Approve & Sync", key=f"app_{task['id']}"):
                    if notion.enabled():
                        notion.create_task(title=task['data'].get('task'), trace_id=task['id'])
                    PersistenceManager.update_event_status(task['id'], "approved")
                    st.rerun()
                if c2.button("Dismiss", key=f"dis_{task['id']}"):
                    PersistenceManager.update_event_status(task['id'], "rejected")
                    st.rerun()

# --- TAB 4: NETWORK (החזרת הממשקים היפים) ---
with tab_network:
    st.subheader("🌐 Integration Hub")
    n1, n2, n3 = st.columns(3)
    with n1:
        st.markdown("### 📧 Gmail")
        st.caption("Status: **Disconnected**")
        st.button("Connect Account", key="g_conn")
    with n2:
        st.markdown("### 📆 Google Calendar")
        st.caption("Status: **Disconnected**")
        st.button("Sync Schedule", key="c_conn")
    with n3:
        st.markdown("### 💬 WhatsApp")
        st.success("🟢 Ready for Webhook")
        st.info("Number: whatsapp:+14155238886")
    
    st.divider()
    st.markdown("### 📝 Notion CMS")
    if notion.enabled():
        st.success("Connected to Notion API")
    else:
        st.warning("Notion: Service Disabled (Using Mock/Null)")

# --- TAB 5: INTERNAL ---
with tab_internal:
    st.subheader("⚙️ System Activity Registry")
    if all_events:
        df = pd.DataFrame(all_events)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        fig = px.histogram(df, x="timestamp", color="type", template="plotly_dark")
        st.plotly_chart(fig, use_container_width=True)
        st.table(df[['timestamp', 'type', 'id']].head(15))

# --- FOOTER ---
st.markdown(f'<div class="footer">Built by Ofir Betesh • {datetime.now().year}</div>', unsafe_allow_html=True)