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

# הגדרות דף - המיתוג של K
st.set_page_config(page_title="KIRP OS", page_icon="🧠", layout="wide")

# --- CUSTOM CSS (The Architect v4.5 - Enterprise Premium) ---
st.markdown("""
    <style>
    /* רקע כללי וצבעים עמוקים */
    .stApp { 
        background-color: #05070a; 
        color: #e0e0e0; 
    }
    
    /* עיצוב ה-Sidebar */
    [data-testid="stSidebar"] { 
        background-color: #080a0f; 
        border-right: 1px solid #1a1c23; 
    }
    
    /* כרטיסי מטריקות עם אפקט זוהר */
    .metric-card { 
        background: linear-gradient(145deg, #0d1117, #161b22);
        padding: 22px; 
        border-radius: 15px; 
        border: 1px solid #30363d;
        text-align: center;
        box-shadow: 0 4px 20px rgba(0,0,0,0.5);
        transition: all 0.3s ease;
    }
    .metric-card:hover { 
        transform: translateY(-5px); 
        border-color: #58a6ff; 
        box-shadow: 0 6px 25px rgba(88, 166, 255, 0.2);
    }
    
    /* נורות סטטוס (LEDs) */
    .led { height: 10px; width: 10px; border-radius: 50%; display: inline-block; margin-right: 8px; }
    .led-green { background-color: #238636; box-shadow: 0 0 10px #238636; }
    .led-blue { background-color: #1f6feb; box-shadow: 0 0 10px #1f6feb; }
    .led-red { background-color: #da3633; box-shadow: 0 0 10px #da3633; }
    
    /* פריטי פעילות אחרונה ב-Sidebar */
    .activity-box {
        background: #0d1117;
        padding: 12px;
        border-radius: 8px;
        margin-bottom: 8px;
        font-size: 0.85rem;
        border-left: 3px solid #58a6ff;
        transition: background 0.2s;
    }
    .activity-box:hover { background: #161b22; }
    
    /* כותרת K גדולה */
    .k-logo {
        font-size: 70px;
        font-weight: 800;
        background: linear-gradient(to bottom, #58a6ff, #1f6feb);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: -10px;
    }

    .footer { 
        position: fixed; 
        bottom: 10px; 
        right: 20px; 
        color: #8b949e; 
        font-size: 11px; 
        font-family: 'Courier New', monospace;
        letter-spacing: 1px;
    }
    
    /* טאבים מעוצבים */
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] {
        background-color: #0d1117;
        border-radius: 8px 8px 0 0;
        padding: 10px 25px;
        color: #8b949e;
    }
    .stTabs [data-baseweb="tab--active"] {
        background-color: #161b22;
        border-bottom: 2px solid #58a6ff !important;
        color: #58a6ff !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- פונקציות עזר (Logic) ---
def get_event_summary(e):
    data = e.get('data', {})
    if 'task' in data: return f"📝 {data['task']}"
    if 'query' in data: return f"❓ {data['query']}"
    if 'text' in data: return f"🧠 {data['text'][:45]}..."
    if 'answer_text' in data: return f"🤖 {data['answer_text'][:45]}..."
    return f"⚙️ {e.get('type', 'System Update')}"

# --- DATA FETCHING ---
all_events = PersistenceManager.get_all_events(limit=100)
m_stats = metrics.snapshot()
pending_tasks = PersistenceManager.get_pending_approvals()
memories = [e for e in all_events if "knowledge" in e.get('type', '') or "memory" in e.get('type', '')]

# --- SIDEBAR (THE BRAIN) ---
with st.sidebar:
    st.markdown('<div class="k-logo">K</div>', unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #8b949e; letter-spacing: 2px;'>INTELLIGENCE OS</p>", unsafe_allow_html=True)
    st.divider()
    
    st.subheader("⚡ Quick Actions")
    suggestions = ["מה המשימות שלי?", "סכם זיכרונות", "הוסף תובנה"]
    for suggest in suggestions:
        if st.button(f"🔍 {suggest}", width='stretch'):
            # שליחה אוטומטית לצ'אט
            if "messages" not in st.session_state: st.session_state.messages = []
            st.session_state.messages.append({"role": "user", "content": suggest})
            with st.spinner("Processing..."):
                res = asyncio.run(agent.query(suggest))
                st.session_state.messages.append({"role": "assistant", "content": res['answer_text']})
            st.rerun()
    
    st.divider()
    st.subheader("🕒 Recent Activity")
    for e in all_events[:10]:
        t = e.get('timestamp', '').split('T')[-1][:5]
        summary = get_event_summary(e)
        st.markdown(f"<div class='activity-box'><b>{t}</b><br>{summary}</div>", unsafe_allow_html=True)

# --- TOP REAL-TIME STATUS BAR ---
st.markdown(f"""
    <div style='text-align: right; padding-bottom: 10px; font-family: monospace; font-size: 0.9rem;'>
        <span class="led led-green"></span> Core Online | 
        <span class="led led-blue"></span> Memory Sync: Active | 
        <span class="led led-blue"></span> WhatsApp: Connected | 
        {datetime.now().strftime("%d/%m/%Y %H:%M")}
    </div>
""", unsafe_allow_html=True)

# --- METRICS DASHBOARD ---
m1, m2, m3, m4 = st.columns(4)
with m1:
    st.markdown(f'<div class="metric-card"><small style="color: #8b949e;">OS STATUS</small><h2 style="color:#238636; margin:0;">ACTIVE</h2><p style="font-size:0.8rem; margin:0;">Latency: {m_stats.get("latency", 42)}ms</p></div>', unsafe_allow_html=True)
with m2:
    st.markdown(f'<div class="metric-card"><small style="color: #8b949e;">PENDING APPROVALS</small><h2 style="margin:0;">{len(pending_tasks)}</h2><p style="font-size:0.8rem; margin:0;">Pipeline Actions</p></div>', unsafe_allow_html=True)
with m3:
    st.markdown(f'<div class="metric-card"><small style="color: #8b949e;">KNOWLEDGE VAULT</small><h2 style="margin:0;">{len(memories)}</h2><p style="font-size:0.8rem; margin:0;">Stored Insights</p></div>', unsafe_allow_html=True)
with m4:
    st.markdown(f'<div class="metric-card"><small style="color: #8b949e;">SYSTEM TRAFFIC</small><h2 style="margin:0;">{m_stats.get("qps", 0)}</h2><p style="font-size:0.8rem; margin:0;">Requests Processed</p></div>', unsafe_allow_html=True)

st.divider()

# --- NAVIGATION TABS ---
tab_chat, tab_vault, tab_actions, tab_network, tab_internal = st.tabs([
    "💬 Intelligence", "🧠 Core Vault", "✅ Action Pipeline", "🌐 Network", "⚙️ Internal Registry"
])

# --- TAB 1: INTELLIGENCE ---
with tab_chat:
    if "messages" not in st.session_state: st.session_state.messages = []
    for m in st.session_state.messages:
        with st.chat_message(m["role"]): st.markdown(m["content"])
    
    if prompt := st.chat_input("Command KIRP OS..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(prompt)
        with st.spinner("Processing Logic..."):
            res = asyncio.run(agent.query(prompt))
            st.session_state.messages.append({"role": "assistant", "content": res['answer_text']})
            if any(word in prompt.lower() for word in ["תזכיר", "צריך", "לקנות", "תזכורת"]):
                st.toast("Task Captured!", icon="✅")
        st.rerun()

# --- TAB 2: CORE VAULT (INGEST) ---
with tab_vault:
    st.subheader("🧠 Memory Ingest")
    v_col1, v_col2 = st.columns([2, 1])
    with v_col1:
        insight = st.text_area("Record a new strategic insight:", placeholder="Type anything that needs to be part of your long-term memory...", height=150)
    with v_col2:
        st.info("🔍 **Auto-Context Engine**")
        if insight:
            detected = "Web/Link" if "http" in insight else "General Insight"
            st.success(f"Detected: **{detected}**")
            if st.button("Archive to Core Vault", width='stretch'):
                PersistenceManager.append_event("knowledge_add", {"text": insight, "source": "UI_Direct"})
                st.balloons()
                st.rerun()

# --- TAB 3: ACTION PIPELINE ---
with tab_actions:
    st.subheader("📋 Governance & Sync")
    if not pending_tasks:
        st.success("All actions synchronized. Pipeline clear.")
    else:
        selected_ids = st.multiselect("Bulk Select Tasks:", [t['id'] for t in pending_tasks])
        if st.button("✅ Bulk Sync to Notion", width='stretch') and selected_ids:
            for eid in selected_ids:
                task_data = next(t for t in pending_tasks if t['id'] == eid)
                if notion.enabled(): notion.create_task(task_data['data'].get('task', 'New Task'), eid)
                PersistenceManager.update_event_status(eid, "approved")
            st.rerun()

        st.divider()
        for task in pending_tasks:
            with st.expander(f"📌 {task['data'].get('task', 'New Action Item')}"):
                st.json(task['data'])
                c1, c2 = st.columns(2)
                if c1.button("Approve & Sync", key=f"app_{task['id']}", width='stretch'):
                    if notion.enabled(): notion.create_task(task['data'].get('task'), task['id'])
                    PersistenceManager.update_event_status(task['id'], "approved")
                    st.rerun()
                if c2.button("Dismiss", key=f"dis_{task['id']}", width='stretch'):
                    PersistenceManager.update_event_status(task['id'], "rejected")
                    st.rerun()

# --- TAB 4: NETWORK ---
with tab_network:
    st.subheader("🌐 Service Integration Hub")
    n1, n2, n3 = st.columns(3)
    with n1:
        st.markdown("### 📧 Gmail")
        st.markdown('<span class="led led-red"></span> Disconnected', unsafe_allow_html=True)
        st.button("Connect Account", key="g_auth", width='stretch')
    with n2:
        st.markdown("### 📆 Google Calendar")
        st.markdown('<span class="led led-red"></span> Disconnected', unsafe_allow_html=True)
        st.button("Authorize Sync", key="c_auth", width='stretch')
    with n3:
        st.markdown("### 💬 WhatsApp")
        st.markdown('<span class="led led-green"></span> Gateway Online', unsafe_allow_html=True)
        st.info("Sandbox Active: +1 415 523 8886")
    
    st.divider()
    if notion.enabled():
        st.success("🟢 Notion CMS: Connected and Syncing")
    else:
        st.warning("🟡 Notion CMS: API Keys Missing (Mock Mode)")

# --- TAB 5: INTERNAL REGISTRY (The Deep Explorer) ---
with tab_internal:
    st.subheader("⚙️ System Registry & Audit Trail")
    if all_events:
        # עיבוד הנתונים לפורמט עשיר
        registry_data = []
        for e in all_events:
            registry_data.append({
                "Timestamp": e.get('timestamp', '')[11:19],
                "Event Type": e.get('type'),
                "Summary": get_event_summary(e),
                "Raw Data / Payload": str(e.get('data', {})),
                "Status": e.get('status', 'logged'),
                "ID": e.get('id')
            })
        
        df_registry = pd.DataFrame(registry_data)
        
        # גרף פעילות קטן ומעוצב
        fig = px.bar(df_registry, x='Event Type', color='Status', template='plotly_dark', height=250)
        fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig, width='stretch')
        
        # הטבלה המלאה עם הנתונים שביקשת
        st.dataframe(df_registry, width='stretch', hide_index=True)

# --- FOOTER (הקרדיט שלך) ---
st.markdown(f'<div class="footer">Built by Ofir Betesh • {datetime.now().year} • KIRP Intelligence v4.5</div>', unsafe_allow_html=True)