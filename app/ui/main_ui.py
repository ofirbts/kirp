# ================================
# KIRP OS – main_ui.py (v6.5 CLEAN)
# ================================

import streamlit as st
import requests
import os
import sys
import asyncio
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, List

import pandas as pd
import plotly.express as px
from dotenv import load_dotenv
import importlib.util

# ----------------
# BOOTSTRAP
# ----------------
load_dotenv()
logger = logging.getLogger("KIRP_UI")

CURRENT_FILE = Path(__file__).resolve()
ROOT_PATH = CURRENT_FILE.parent.parent.parent
if str(ROOT_PATH) not in sys.path:
    sys.path.insert(0, str(ROOT_PATH))

# ----------------
# CONFIG
# ----------------
CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
INTERNAL_API_URL = os.getenv("INTERNAL_API_URL", "http://kirp-api:8000")
EXTERNAL_URL = os.getenv("EXTERNAL_URL", "http://localhost:8501").rstrip("/")
REDIRECT_URI = f"{EXTERNAL_URL}/"

st.set_page_config(
    page_title="🧠 KIRP OS",
    page_icon="🧠",
    layout="wide",
)

# ----------------
# SESSION STATE
# ----------------
DEFAULT_STATE = {
    "authenticated": False,
    "auth_checked": False,
    "user_id": None,
    "full_name": None,
    "avatar_url": None,
    "messages": [],
    "processed_codes": set(),
}

for k, v in DEFAULT_STATE.items():
    st.session_state.setdefault(k, v)

# ----------------
# CORE LOADER
# ----------------
def load_module(path: Path, attr: str):
    spec = importlib.util.spec_from_file_location(attr, str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return getattr(mod, attr)

PersistenceManager = None
Agent = None

try:
    PersistenceManager = load_module(
        ROOT_PATH / "app/core/persistence.py",
        "PersistenceManager"
    )()
    logger.info("Persistence loaded")
except Exception as e:
    logger.error(f"Persistence load failed: {e}")

try:
    Agent = load_module(
        ROOT_PATH / "app/agent/agent.py",
        "agent"
    )
    logger.info("Agent loaded")
except Exception as e:
    logger.error(f"Agent load failed: {e}")

# ----------------
# AUTH MANAGER
# ----------------
class Auth:
    @staticmethod
    def restore():
        if st.session_state.auth_checked:
            return
        st.session_state.auth_checked = True
        try:
            import extra_streamlit_components as stx
            cm = stx.CookieManager(key="kirp_auth")
            uid = cm.get("kirp_user_id")
            if uid:
                st.session_state.update({
                    "authenticated": True,
                    "user_id": uid,
                    "full_name": uid,
                })
        except:
            pass

    @staticmethod
    def login(user: Dict[str, Any]):
        st.session_state.update({
            "authenticated": True,
            "user_id": user.get("user_id"),
            "full_name": user.get("full_name", user.get("user_id")),
            "avatar_url": user.get("avatar_url"),
        })
        try:
            import extra_streamlit_components as stx
            cm = stx.CookieManager(key="kirp_auth")
            cm.set(
                "kirp_user_id",
                st.session_state.user_id,
                expires_at=datetime.now() + timedelta(days=30)
            )
        except:
            pass

    @staticmethod
    def logout():
        for k in DEFAULT_STATE:
            st.session_state[k] = DEFAULT_STATE[k]
        try:
            import extra_streamlit_components as stx
            stx.CookieManager(key="kirp_auth").delete("kirp_user_id")
        except:
            pass
        st.rerun()

Auth.restore()

# ----------------
# GOOGLE CALLBACK
# ----------------
if "code" in st.query_params and not st.session_state.authenticated:
    code = st.query_params["code"]
    if code not in st.session_state.processed_codes:
        st.session_state.processed_codes.add(code)
        try:
            resp = requests.post(
                f"{INTERNAL_API_URL}/auth/google/callback",
                json={"code": code},
                timeout=10,
            )
            if resp.status_code == 200:
                Auth.login(resp.json())
        finally:
            st.query_params.clear()
            st.rerun()

# ----------------
# LOGIN SCREEN
# ----------------
if not st.session_state.authenticated:
    st.title("🧠 KIRP OS")
    c1, c2 = st.columns(2)

    with c1:
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")
        if st.button("Login", use_container_width=True):
            r = requests.post(
                f"{INTERNAL_API_URL}/auth/login",
                json={"username": u, "password": p},
                timeout=10,
            )
            if r.status_code == 200:
                Auth.login(r.json())
                st.rerun()
            else:
                st.error("Invalid credentials")

    with c2:
        google_url = (
            "https://accounts.google.com/o/oauth2/v2/auth"
            f"?client_id={CLIENT_ID}"
            "&response_type=code"
            "&scope=openid email profile"
            f"&redirect_uri={REDIRECT_URI}"
        )
        st.markdown(
            f"<a href='{google_url}'><button style='width:100%'>Google Login</button></a>",
            unsafe_allow_html=True,
        )

    st.stop()

# ----------------
# HELPERS
# ----------------
def run_agent(prompt: str) -> str:
    if not Agent:
        return "🤖 Agent unavailable"
    try:
        return asyncio.run(
            Agent.query(prompt, st.session_state.user_id)
        ).get("answer_text", "")
    except Exception as e:
        return f"Error: {e}"

# ----------------
# SIDEBAR
# ----------------
with st.sidebar:
    st.markdown(f"### 👤 {st.session_state.full_name}")
    if st.button("🚪 Logout", use_container_width=True):
        Auth.logout()

# ----------------
# DASHBOARD
# ----------------
st.success(f"Welcome {st.session_state.full_name}")

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Messages", len(st.session_state.messages))
with col2:
    count = (
        len(PersistenceManager.get_user_events(st.session_state.user_id, 100))
        if PersistenceManager else 0
    )
    st.metric("Memories", count)
with col3:
    st.metric("Status", "LIVE")

# ----------------
# TABS
# ----------------
tab_chat, tab_memory, tab_tasks, tab_analytics, tab_system = st.tabs(
    ["🤖 Chat", "🧠 Knowledge", "✅ Tasks", "📊 Analytics", "⚙️ System"]
)

# ---- CHAT
with tab_chat:
    for m in st.session_state.messages:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])

    prompt = st.chat_input("Ask KIRP…")
    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        reply = run_agent(prompt)
        st.session_state.messages.append({"role": "assistant", "content": reply})
        st.rerun()

# ---- KNOWLEDGE
with tab_memory:
    text = st.text_area("Add knowledge")
    if st.button("Save") and text and PersistenceManager:
        PersistenceManager.append_event(
            st.session_state.user_id,
            "knowledge",
            {"text": text},
        )
        st.success("Saved")

# ---- TASKS
with tab_tasks:
    if PersistenceManager:
        tasks = PersistenceManager.get_pending_approvals(st.session_state.user_id)
        if not tasks:
            st.success("No pending tasks")
        for t in tasks:
            with st.expander(t.get("type", "Task")):
                st.json(t)

# ---- ANALYTICS
with tab_analytics:
    if PersistenceManager:
        events = PersistenceManager.get_user_events(st.session_state.user_id, 200)
        if events:
            df = pd.DataFrame(events)
            fig = px.histogram(df, x="timestamp", color="type")
            st.plotly_chart(fig, use_container_width=True)

# ---- SYSTEM
with tab_system:
    st.json({
        "user": st.session_state.user_id,
        "messages": len(st.session_state.messages),
        "time": datetime.now().isoformat(),
    })

# ----------------
# FOOTER
# ----------------
st.markdown(
    f"<div style='text-align:center;color:#888;margin-top:3rem'>"
    f"KIRP OS • {datetime.now().year} • Built by Ofir Betesh"
    f"</div>",
    unsafe_allow_html=True,
)