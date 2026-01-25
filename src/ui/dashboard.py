"""
Streamlit MVP Dashboard — Today Plan, Risks, Agent Activity, Health, Insights, Live Event Flow.
"""

from __future__ import annotations

import logging
import os
import asyncio
from typing import Any

logger = logging.getLogger(__name__)


def run_dashboard() -> None:
    """Run Streamlit dashboard. Entrypoint for streamlit run src/ui/dashboard.py."""
    import streamlit as st

    st.set_page_config(
        page_title="KIRP Enterprise — Intelligence OS",
        page_icon="🧠",
        layout="wide",
    )
    st.title("KIRP Enterprise — Intelligence OS")
    st.markdown("Controlled Intelligence Layer · Event-Sourced · Multi-Tenant · Zero Leakage")

    api_url = os.getenv("API_URL", "http://localhost:8000")
    tab_main, tab_agents, tab_insights, tab_governance, tab_health = st.tabs(
        ["Main", "Agents", "Insights", "Governance", "Health"]
    )

    with tab_main:
        st.subheader("Today Plan")
        st.info("Run agents (Planner, Forecaster) to populate.")
        st.subheader("Risks & Opportunities")
        st.info("Run RiskOpportunityAgent to populate.")
        st.subheader("Recent Insights")
        st.info("Run insights API to populate.")
        st.subheader("Live Event Flow")
        st.info("Connect to event bus / Kafka for live flow.")

    with tab_agents:
        st.subheader("Agent Registry")
        try:
            from src.ui.api import KIRPApiClient
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            client = KIRPApiClient(api_url)
            agents = loop.run_until_complete(client.agents())
            for a in agents:
                st.write("- **%s** — %s" % (a.get("name", "?"), a.get("description", "")))
            loop.close()
        except Exception as e:
            st.error("API unavailable: %s" % str(e))

    with tab_insights:
        st.subheader("Insights")
        st.info("POST /api/v1/query + insights engine.")

    with tab_governance:
        st.subheader("Shared Spaces")
        st.info("Tenant engine + RBAC.")
        st.subheader("Approvals")
        st.info("Governance engine + OPA.")
        st.subheader("Audit Logs")
        st.info("Governance audit trail.")

    with tab_health:
        st.subheader("System Health")
        try:
            from src.ui.api import KIRPApiClient
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            client = KIRPApiClient(api_url)
            health = loop.run_until_complete(client.health())
            st.json(health)
            loop.close()
        except Exception as e:
            st.error("Health check failed: %s" % str(e))

    st.sidebar.markdown("### KIRP v0.1")
    st.sidebar.markdown("Event -> RAG -> Agent -> Governance -> Execution -> Event")


if __name__ == "__main__":
    run_dashboard()
