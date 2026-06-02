"""
UI — Dashboard (Streamlit MVP), API bindings, realtime.

Main Dashboard: Today Plan, Risks & Opportunities, Agent Activity,
System Health, Recent Insights, Live Event Flow.
"""

from src.ui.api import KIRPApiClient
from src.ui.dashboard import run_dashboard
from src.ui.realtime import RealtimeClient

__all__ = ["KIRPApiClient", "run_dashboard", "RealtimeClient"]
