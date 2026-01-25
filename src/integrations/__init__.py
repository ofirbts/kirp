"""
Integrations Hub — Inbound ingestion → Events; Outbound execution → Actions.

Each integration supports:
- Inbound ingestion → Events
- Outbound execution → Actions
- Real-time notifications

Required: Notion, WhatsApp, Slack, Email, Calendar, Webhooks.
"""

from src.integrations.notion import NotionIntegration
from src.integrations.whatsapp import WhatsAppIntegration
from src.integrations.slack import SlackIntegration
from src.integrations.email import EmailIntegration
from src.integrations.calendar import CalendarIntegration

__all__ = [
    "NotionIntegration",
    "WhatsAppIntegration",
    "SlackIntegration",
    "EmailIntegration",
    "CalendarIntegration",
]
