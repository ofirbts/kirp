"""
Governance Dashboard — Streamlit UI for approvals, audit, policy simulation.

Tabs: Audit Logs, Approvals, Policy Simulation, Live Metrics.
"""

from __future__ import annotations

import logging
import os
from typing import Any

import streamlit as st

logger = logging.getLogger(__name__)

API_BASE = os.getenv("API_URL", "http://localhost:8000")


def run_governance_dashboard() -> None:
    """Run Streamlit governance dashboard."""
    st.set_page_config(
        page_title="KIRP Governance",
        page_icon="🔒",
        layout="wide",
    )
    st.title("KIRP Governance & Observability")
    st.markdown("Approvals · Audit Logs · Policy Simulation · Live Metrics")

    tab_audit, tab_approval, tab_policy, tab_live = st.tabs(
        ["Audit Logs", "Approvals", "Policy Simulation", "Live Metrics"]
    )

    with tab_audit:
        st.subheader("Audit Logs")
        actor = st.text_input("Filter by actor (optional)")
        event_type = st.text_input("Filter by event type (optional)")
        limit = st.number_input("Limit", min_value=1, max_value=500, value=100)
        if st.button("Fetch audit logs"):
            try:
                import requests
                params: dict[str, Any] = {"limit": limit}
                if event_type:
                    params["event_type"] = event_type
                r = requests.get(
                    f"{API_BASE}/governance/audit",
                    params=params,
                    timeout=10,
                )
                r.raise_for_status()
                data = r.json()
                st.json(data)
                st.info(f"Found {data.get('count', 0)} events")
            except Exception as e:
                st.error(f"Failed to fetch audit logs: {e}")

    with tab_approval:
        st.subheader("Approval Center")
        st.markdown("### Pending Approvals")
        try:
            import requests
            r = requests.get(f"{API_BASE}/governance/approvals", timeout=10)
            r.raise_for_status()
            data = r.json()
            pending = data.get("pending", [])
            st.info(f"{data.get('count', 0)} pending approvals")

            for ev in pending[:20]:
                ev_id = ev.get("id", "unknown")
                with st.expander(f"Event {ev_id[:8]}... — {ev.get('event_type', 'unknown')}"):
                    st.json(ev)
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button(f"Approve {ev_id[:8]}", key=f"approve_{ev_id}"):
                            try:
                                r2 = requests.post(
                                    f"{API_BASE}/governance/approve/{ev_id}",
                                    timeout=10,
                                )
                                r2.raise_for_status()
                                st.success("Approved!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Approval failed: {e}")
                    with col2:
                        if st.button(f"Reject {ev_id[:8]}", key=f"reject_{ev_id}"):
                            try:
                                r2 = requests.post(
                                    f"{API_BASE}/governance/reject/{ev_id}",
                                    timeout=10,
                                )
                                r2.raise_for_status()
                                st.success("Rejected!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Rejection failed: {e}")
        except Exception as e:
            st.error(f"Failed to fetch approvals: {e}")

    with tab_policy:
        st.subheader("Policy Simulation")
        policy_id = st.text_input("Policy ID", value="default_policy")
        if st.button("Run simulation"):
            try:
                import requests
                r = requests.post(
                    f"{API_BASE}/governance/policy-simulate",
                    json={"policy_id": policy_id, "change_set": {}},
                    timeout=10,
                )
                r.raise_for_status()
                data = r.json()
                st.json(data)
                st.metric("Simulated Risk", f"{data.get('simulated_risk', 0):.2%}")
            except Exception as e:
                st.error(f"Policy simulation failed: {e}")

    with tab_live:
        st.subheader("Live Metrics")
        st.markdown("Connect to Prometheus / Elastic and MetricsAgent")
        try:
            import requests
            r = requests.get(f"{API_BASE}/observability/metrics/snapshot", timeout=5)
            r.raise_for_status()
            data = r.json()
            st.json(data)
        except Exception as e:
            st.error(f"Metrics unavailable: {e}")


if __name__ == "__main__":
    run_governance_dashboard()
