"""E2E: Mock Twilio send_whatsapp; Mock LinkedIn post_text."""
import os
from unittest.mock import patch, MagicMock

import pytest

try:
    import twilio
except ImportError:
    twilio = None


def test_send_whatsapp_missing_env():
    with patch.dict(os.environ, {}, clear=False):
        for k in list(os.environ.keys()):
            if k.startswith("TWILIO"):
                del os.environ[k]
        from brand_os_integrations.whatsapp import send_whatsapp
        result = send_whatsapp("+1234567890", "test")
        assert result.get("ok") is False
        assert "TWILIO" in result.get("error", "")


@pytest.mark.skipif(twilio is None, reason="twilio not installed")
@patch("twilio.rest.Client")
def test_send_whatsapp_with_mock(mock_client):
    mock_client.return_value.messages.create.return_value = MagicMock(sid="SM123", status="sent")
    with patch.dict(os.environ, {"TWILIO_SID": "x", "TWILIO_TOKEN": "y", "TWILIO_WHATSAPP_FROM": "whatsapp:+14155238886"}):
        from brand_os_integrations.whatsapp import send_whatsapp
        result = send_whatsapp("+1234567890", "Hello")
        assert result.get("ok") is True
        assert result.get("sid") == "SM123"


def test_post_text_missing_token():
    with patch.dict(os.environ, {}, clear=False):
        if "LINKEDIN_ACCESS_TOKEN" in os.environ:
            del os.environ["LINKEDIN_ACCESS_TOKEN"]
        from brand_os_integrations.linkedin import post_text
        result = post_text("Hello")
        assert result.get("ok") is False
