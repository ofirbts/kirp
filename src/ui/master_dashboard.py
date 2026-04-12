"""
KIRP Enterprise — Master Dashboard.

North Star: Controlled Intelligence Layer · Event-Sourced · Multi-Tenant · Zero Leakage.

Tabs: Today Intelligence | Risks & Opportunities | Search | Agents | Health |
      Governance | Insights | Live Flow
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

import requests
import streamlit as st

logger = logging.getLogger(__name__)

API_URL = os.getenv("API_URL", "http://localhost:8000")


def _get(path: str, **kwargs: Any) -> dict[str, Any] | list[Any]:
    try:
        r = requests.get(f"{API_URL}{path}", timeout=15, **kwargs)
        r.raise_for_status()
        return r.json() if r.content else {}
    except Exception as e:
        logger.warning("GET %s failed: %s", path, e)
        return {}


def _post(path: str, json: dict[str, Any] | None = None, **kwargs: Any) -> dict[str, Any] | list[Any]:
    try:
        r = requests.post(f"{API_URL}{path}", json=json or {}, timeout=15, **kwargs)
        r.raise_for_status()
        return r.json() if r.content else {}
    except Exception as e:
        logger.warning("POST %s failed: %s", path, e)
        return {}


def run() -> None:
    st.set_page_config(
        page_title="KIRP Enterprise — Intelligence OS",
        page_icon="🧠",
        layout="wide",
    )
    st.title("🧠 KIRP Enterprise — Intelligence OS")
    st.caption(
        "Controlled Intelligence Layer · Event-Sourced · Multi-Tenant · Zero Leakage"
    )
    st.markdown("---")

    tab_intel, tab_risks, tab_search, tab_agents, tab_health, tab_gov, tab_insights, tab_flow = st.tabs([
        "📊 Today Intelligence",
        "⚠️ Risks & Opportunities",
        "🔍 Search",
        "🤖 Agents",
        "📈 Health",
        "🔐 Governance",
        "💡 Insights",
        "📡 Live Flow",
    ])

    with tab_intel:
        st.subheader("Quick Ingest")
        with st.form("ingest_form"):
            ci_tenant = st.text_input("Tenant", value="default")
            ci_space = st.text_input("Space", value="private")
            ci_user = st.text_input("User", value="ofir")
            ci_content = st.text_area("Content", value="Finish KIRP refactor by Friday")
            if st.form_submit_button("Ingest"):
                out = _post("/api/v1/ingest", json={
                    "tenant_id": ci_tenant,
                    "space_id": ci_space,
                    "user_id": ci_user,
                    "content": ci_content,
                    "source": "ui",
                })
                if isinstance(out, dict) and out.get("ok"):
                    st.success(f"Event ingested: {out.get('event_id')}")
                else:
                    st.error(str(out))
        st.divider()
        st.subheader("Today Plan & Critical Actions")
        if st.button("Fetch today intelligence"):
            data = _post(
                "/api/v1/query",
                json={
                    "query": "What are my 3 most critical actions for today?",
                    "k": 10,
                },
            )
            if isinstance(data, dict) and data.get("ok"):
                for i, r in enumerate((data.get("results") or [])[:5], 1):
                    st.markdown(f"**{i}.** {r.get('text', '')[:200]}")
                    st.caption(f"Source: {r.get('source')} · Score: {r.get('score', 0):.2f}")
            else:
                st.info("Run ingest first, then query.")
        st.divider()
        wi = _get("/whatsapp/daily-intelligence", params={"user_id": "ofir", "tenant_id": "default", "space_id": "private"})
        if isinstance(wi, dict) and wi.get("ok"):
            st.success("WhatsApp daily intelligence ready.")
            st.json(wi)
        else:
            st.info("WhatsApp daily intelligence: configure WHATSAPP_DEFAULT_TO or run manually.")

    with tab_risks:
        st.subheader("Risks & Opportunities")
        data = _post(
            "/api/v1/query",
            json={"query": "Risks and opportunities", "k": 10},
        )
        if isinstance(data, dict) and data.get("results"):
            for r in data["results"][:5]:
                st.markdown(f"- **{r.get('text', '')[:150]}**")
        else:
            st.info("Ingest events, then query for risks.")

    with tab_search:
        st.subheader("Universal Search")
        q = st.text_input("Query", placeholder="Search knowledge, tasks, events…")
        if st.button("Search") and q:
            data = _post("/api/v1/query", json={"query": q, "k": 20})
            if isinstance(data, dict) and data.get("results"):
                for r in data["results"]:
                    st.markdown(f"- {r.get('text', '')[:200]}")
            else:
                st.warning("No results.")

    with tab_agents:
        st.subheader("Agent Registry")
        agents = _get("/api/v1/agents")
        if isinstance(agents, list):
            for a in agents:
                with st.expander(f"**{a.get('name')}** — {a.get('type')}"):
                    st.write(a.get("description", ""))
                    st.caption(f"Triggers: {', '.join(a.get('triggers', []))}")
        else:
            st.warning("Agents unavailable.")

    with tab_health:
        st.subheader("System Health")
        h = _get("/health")
        if isinstance(h, dict):
            st.json(h)
        ob = _get("/observability/health")
        if isinstance(ob, dict):
            st.subheader("Observability")
            st.json(ob)
        metrics = _get("/observability/metrics/snapshot")
        if isinstance(metrics, dict):
            st.subheader("Metrics")
            st.json(metrics)

    with tab_gov:
        st.subheader("Governance — Approvals & Audit")
        approvals = _get("/governance/approvals")
        if isinstance(approvals, dict):
            st.metric("Pending", approvals.get("count", 0))
            for e in (approvals.get("pending") or [])[:5]:
                st.json(e)
        audit = _get("/governance/audit", params={"limit": 20})
        if isinstance(audit, dict):
            st.subheader("Audit log")
            st.json(audit.get("events", [])[:5])

    with tab_insights:
        st.subheader("Insights")
        ins = _get("/api/v1/insights", params={"tenant_id": "default", "user_id": "ofir"})
        if isinstance(ins, list) and ins:
            st.json(ins)
        else:
            st.info("Insights engine placeholder.")

    with tab_flow:
        st.subheader("Live Event Flow")
        st.markdown("Pipeline: **Event → RAG → Agent → Governance → Execution → Event**")
        
        # Live event stream
        if st.button("Start Live Stream"):
            st.session_state["live_stream_active"] = True
        
        if st.button("Stop Live Stream"):
            st.session_state["live_stream_active"] = False
        
        if st.session_state.get("live_stream_active"):
            # Fetch recent events
            import time
            from datetime import datetime, timedelta
            
            placeholder = st.empty()
            
            # Poll for events
            since = datetime.now() - timedelta(minutes=5)
            events_data = _get("/governance/audit", params={
                "limit": 50,
                "event_type": None,
            })
            
            if isinstance(events_data, dict):
                events = events_data.get("events", [])
                
                # Filter recent events
                recent_events = []
                for ev in events:
                    ev_time = ev.get("timestamp")
                    if ev_time:
                        try:
                            if isinstance(ev_time, str):
                                ev_dt = datetime.fromisoformat(ev_time.replace("Z", "+00:00"))
                            else:
                                ev_dt = ev_time
                            if ev_dt >= since:
                                recent_events.append(ev)
                        except Exception:
                            pass
                
                # Display events
                with placeholder.container():
                    st.metric("Recent Events (5min)", len(recent_events))
                    
                    # Event timeline
                    for ev in recent_events[:20]:  # Show last 20
                        ev_type = ev.get("event_type", "unknown")
                        ev_time = ev.get("timestamp", "")
                        ev_content = ev.get("content", "")[:100]
                        trace_id = ev.get("trace_id", "")
                        
                        with st.expander(f"**{ev_type}** — {ev_time[:19] if ev_time else 'N/A'}"):
                            st.write(f"**Content:** {ev_content}")
                            st.caption(f"Trace: `{trace_id}` | Tenant: {ev.get('tenant_id', 'N/A')} | Space: {ev.get('space_id', 'N/A')}")
                            if ev.get("metadata"):
                                st.json(ev.get("metadata"))
                
                # Auto-refresh
                time.sleep(2)
                st.rerun()
        else:
            st.info("Click 'Start Live Stream' to view real-time events.")
            
            # Show recent events snapshot
            events_data = _get("/governance/audit", params={"limit": 10})
            if isinstance(events_data, dict):
                events = events_data.get("events", [])[:5]
                if events:
                    st.subheader("Recent Events Snapshot")
                    for ev in events:
                        st.text(f"[{ev.get('event_type', 'unknown')}] {ev.get('content', '')[:80]}")

    st.sidebar.markdown("### 🧠 KIRP v1")
    st.sidebar.markdown("Event → RAG → Agent → Governance → Execution → Event")
    st.sidebar.markdown("---")
    st.sidebar.markdown(f"**API:** `{API_URL}`")
    st.sidebar.markdown("**Dashboard:** http://localhost:8501")


if __name__ == "__main__":
    run()
