"""
Email Integration — Inbound + Outbound.

- Inbound: IMAP / webhooks → Events
- Outbound: send via SMTP
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class EmailIntegration:
    """Email ingest + send."""

    def __init__(self) -> None:
        import os
        self._smtp_host = os.getenv("SMTP_HOST", "")
        self._imap_host = os.getenv("IMAP_HOST", "")
        self._user = os.getenv("EMAIL_USER", "")
        self._password = os.getenv("EMAIL_PASSWORD", "")

    async def send(self, to: str, subject: str, body: str, user_id: str = "system") -> dict[str, Any]:
        """Send email. Outbound action."""
        if not self._smtp_host or not self._user:
            logger.warning("Email not configured")
            return {"ok": False, "error": "Email not configured"}
        try:
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
            msg = MIMEMultipart()
            msg["Subject"] = subject
            msg["From"] = self._user
            msg["To"] = to
            msg.attach(MIMEText(body, "plain"))
            with smtplib.SMTP(self._smtp_host, 587) as s:
                s.starttls()
                s.login(self._user, self._password)
                s.sendmail(self._user, [to], msg.as_string())
            return {"ok": True}
        except Exception as e:
            logger.error("Email send failed: %s", e)
            return {"ok": False, "error": str(e)}

    async def fetch_recent(self, tenant_id: str, space_id: str, user_id: str, limit: int = 50) -> list[dict[str, Any]]:
        """Fetch recent emails as event payloads."""
        if not self._imap_host or not self._user:
            return []
        events: list[dict[str, Any]] = []
        try:
            import imaplib
            import email
            m = imaplib.IMAP4_SSL(self._imap_host)
            m.login(self._user, self._password)
            m.select("INBOX")
            _, ids = m.search(None, "ALL")
            for uid in list(reversed(ids[0].split()))[:limit]:
                _, data = m.fetch(uid, "(RFC822)")
                raw = data[0][1]
                msg = email.message_from_bytes(raw)
                subj = msg.get("Subject", "")
                body = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            body = part.get_payload(decode=True).decode(errors="ignore")
                            break
                else:
                    body = msg.get_payload(decode=True).decode(errors="ignore") if msg.get_payload() else ""
                events.append({
                    "tenant_id": tenant_id,
                    "space_id": space_id,
                    "user_id": user_id,
                    "source": "email",
                    "content": f"{subj}\n\n{body[:5000]}",
                    "metadata": {"from": msg.get("From"), "date": msg.get("Date")},
                })
            m.logout()
        except Exception as e:
            logger.error("Email fetch failed: %s", e)
        return events
