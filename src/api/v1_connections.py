"""
Connections API — List, connect, disconnect, sync, validate, and error logs for all integrations.

Supports OAuth (Gmail, Calendar, Slack, Notion) and token-based (WhatsApp, Email, Webhook).
"""

from __future__ import annotations

import logging
import os
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Body, Request
from fastapi.responses import RedirectResponse

from src.auth.tenant_context import get_tenant_context
from src.core.connector_tokens import ConnectorTokenStore, INTEGRATIONS
from src.core.connector_sync_log import ConnectorSyncLogStore

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["connections"])


def _ctx_ids(request: Request) -> tuple[str, str]:
    """Derive tenant_id and user_id from JWT context."""
    ctx = get_tenant_context(request)
    return ctx.tenant_id, ctx.user_id

CONNECTOR_LABELS = {
    "gmail": "Gmail",
    "calendar": "Google Calendar",
    "slack": "Slack",
    "whatsapp": "WhatsApp",
    "notion": "Notion",
    "email": "Email (SMTP)",
    "webhook": "Custom Webhooks",
}


def _token_store() -> ConnectorTokenStore:
    mongo = os.getenv("MONGO_URI", "mongodb://root:example@localhost:27017/kirp?authSource=admin")
    return ConnectorTokenStore(mongo)


def _sync_log_store() -> ConnectorSyncLogStore:
    mongo = os.getenv("MONGO_URI", "mongodb://root:example@localhost:27017/kirp?authSource=admin")
    return ConnectorSyncLogStore(mongo)


async def _ensure_stores():
    ts = _token_store()
    sl = _sync_log_store()
    await ts.connect()
    await sl.connect()
    return ts, sl


@router.get("/connections")
async def list_connections(request: Request) -> dict[str, Any]:
    """
    List all integrations with status. Tenant/user from JWT.
    """
    tenant_id, user_id = _ctx_ids(request)
    ts, sl = await _ensure_stores()
    connected = await ts.list_connected(tenant_id, user_id)
    connectors = []
    for name in INTEGRATIONS:
        status = await sl.get_status(tenant_id, user_id, name)
        is_connected = name in connected
        last_status = (status or {}).get("last_sync_status", "never")
        if is_connected and last_status == "error":
            display_status = "error"
        elif is_connected:
            display_status = "connected"
        else:
            display_status = "not_connected"
        connectors.append({
            "integration": name,
            "label": CONNECTOR_LABELS.get(name, name),
            "status": display_status,
            "connected": is_connected,
            "last_sync_at": (status or {}).get("last_sync_at"),
            "last_sync_status": (status or {}).get("last_sync_status"),
            "last_sync_result": (status or {}).get("last_sync_result") or {},
            "error_count": len((status or {}).get("error_log") or []),
        })
    return {"ok": True, "connectors": connectors, "tenant_id": tenant_id, "user_id": user_id}


@router.post("/connections/{integration}/connect")
async def connect_integration(
    request: Request,
    integration: str,
    body: dict[str, Any] | None = Body(None),
) -> dict[str, Any]:
    """
    Store token for integration. Tenant/user from JWT.
    """
    tenant_id, user_id = _ctx_ids(request)
    if integration not in INTEGRATIONS:
        raise HTTPException(status_code=400, detail=f"Unknown integration: {integration}")
    body = body or {}
    raw = body.get("access_token") or (body.get("extra") or {}).get("api_key") or (body.get("extra") or {}).get("webhook_url")
    access_token = (raw or "").strip() if isinstance(raw, str) else raw
    if not access_token:
        raise HTTPException(status_code=400, detail="access_token or extra.api_key or extra.webhook_url required")
    ts, _ = await _ensure_stores()
    try:
        await ts.set_token(
            tenant_id=tenant_id,
            user_id=user_id,
            integration=integration,
            access_token=access_token,
            refresh_token=body.get("refresh_token"),
            extra=body.get("extra"),
        )
    except Exception as e:
        logger.exception("Connect %s failed: %s", integration, e)
        raise HTTPException(status_code=500, detail=f"Failed to save token: {e!s}")
    return {"ok": True, "integration": integration, "message": "Connected"}


@router.post("/connections/{integration}/disconnect")
async def disconnect_integration(request: Request, integration: str) -> dict[str, Any]:
    """Remove stored token for this integration. Tenant/user from JWT."""
    tenant_id, user_id = _ctx_ids(request)
    if integration not in INTEGRATIONS:
        raise HTTPException(status_code=400, detail=f"Unknown integration: {integration}")
    ts, _ = await _ensure_stores()
    deleted = await ts.delete_token(tenant_id=tenant_id, user_id=user_id, integration=integration)
    return {"ok": True, "integration": integration, "disconnected": deleted}


@router.post("/connections/{integration}/sync")
async def sync_now(request: Request, integration: str, space_id: str = Query("all")) -> dict[str, Any]:
    """Trigger a manual sync for this integration. Tenant/user from JWT."""
    tenant_id, user_id = _ctx_ids(request)
    if integration not in INTEGRATIONS:
        raise HTTPException(status_code=400, detail=f"Unknown integration: {integration}")
    ts, sl = await _ensure_stores()
    token = await ts.get_token(tenant_id, user_id, integration)
    if not token and integration not in ("notion", "email", "webhook"):
        raise HTTPException(status_code=400, detail="Not connected. Connect first.")
    try:
        if integration == "gmail":
            from src.integrations.gmail import GmailIntegration
            from src.workers.connector_sync import run_gmail_sync
            gmail = GmailIntegration(token=token)
            gmail.connect()
            status = await sl.get_status(tenant_id, user_id, "gmail")
            page_token = (status.get("last_sync_result") or {}).get("page_token") if status else None
            result = await run_gmail_sync(tenant_id=tenant_id, space_id=space_id, user_id=user_id, gmail=gmail, page_token=page_token)
        elif integration == "calendar":
            from src.integrations.calendar import CalendarIntegration
            from src.workers.connector_sync import run_calendar_sync
            cal = CalendarIntegration(token=token)
            cal.connect()
            status = await sl.get_status(tenant_id, user_id, "calendar")
            sync_token = (status.get("last_sync_result") or {}).get("sync_token") if status else None
            result = await run_calendar_sync(tenant_id=tenant_id, space_id=space_id, user_id=user_id, calendar=cal, sync_token=sync_token)
        elif integration == "slack":
            ch = (token or {}).get("extra", {}).get("channel_id") or os.getenv("SLACK_SYNC_CHANNEL_ID", "")
            if not ch:
                raise HTTPException(status_code=400, detail="channel_id required for Slack sync; set in connect extra or SLACK_SYNC_CHANNEL_ID")
            from src.integrations.slack import SlackIntegration
            from src.workers.connector_sync import run_slack_sync
            slack = SlackIntegration(access_token=token.get("access_token") if token else None)
            slack.connect()
            result = await run_slack_sync(tenant_id=tenant_id, space_id=space_id, user_id=user_id, channel_id=ch, slack=slack)
        elif integration == "notion":
            from src.integrations.notion import NotionIntegration
            from src.workers.notion_sync import run_notion_sync
            notion = None
            if token and token.get("access_token"):
                notion = NotionIntegration(token=token["access_token"])
                notion.connect()
            result = await run_notion_sync(tenant_id=tenant_id, space_id=space_id, user_id=user_id, notion=notion)
        elif integration in ("whatsapp", "email", "webhook"):
            # Webhook-based: no pull/sync; messages arrive via POST to /api/v1/webhooks/whatsapp etc.
            result = {"message": "No sync for webhook-based integrations; messages arrive when sent to your webhook URL."}
            await sl.record_sync(
                tenant_id=tenant_id,
                user_id=user_id,
                integration=integration,
                status="ok",
                result=result,
                error_message=None,
                clear_errors=True,
            )
            return {"ok": True, "integration": integration, "result": result}
        else:
            raise HTTPException(status_code=400, detail=f"Sync not implemented for {integration}")
        errs = result.get("errors") or []
        status = "error" if errs else "ok"
        await sl.record_sync(
            tenant_id=tenant_id,
            user_id=user_id,
            integration=integration,
            status=status,
            result=result,
            error_message="; ".join(errs[:3]) if errs else None,
        )
        if status == "error":
            try:
                from src.core.notifications import notify_user
                await notify_user(tenant_id, user_id, "sync_error", f"{integration} sync failed", "; ".join(errs[:2]) or "Sync error", space_id=space_id, meta={"integration": integration})
            except Exception:
                pass
            try:
                from src.core.history import record_history
                await record_history(tenant_id, space_id or "all", user_id, "system", f"{integration} sync failed", "; ".join(errs[:2]) or "Sync error", source=integration, meta={"integration": integration})
            except Exception:
                pass
        return {"ok": True, "integration": integration, "result": result}
    except Exception as e:
        logger.exception("Sync failed for %s: %s", integration, e)
        sl_log = _sync_log_store()
        await sl_log.connect()
        await sl_log.record_sync(
            tenant_id=tenant_id,
            user_id=user_id,
            integration=integration,
            status="error",
            result={},
            error_message=str(e),
        )
        try:
            from src.core.notifications import notify_user
            await notify_user(tenant_id, user_id, "sync_error", f"{integration} sync failed", str(e)[:200], space_id=space_id, meta={"integration": integration})
        except Exception:
            pass
        try:
            from src.core.history import record_history
            await record_history(tenant_id, space_id or "all", user_id, "system", f"{integration} sync failed", str(e)[:200], source=integration, meta={"integration": integration})
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/connections/{integration}/validate")
async def validate_connection(
    integration: str,
    tenant_id: str = Query("default"),
    user_id: str = Query("system"),
) -> dict[str, Any]:
    """Check if the stored token is valid (e.g. call a minimal API)."""
    if integration not in INTEGRATIONS:
        raise HTTPException(status_code=400, detail=f"Unknown integration: {integration}")
    ts, _ = await _ensure_stores()
    token = await ts.get_token(tenant_id, user_id, integration)
    if not token:
        return {"ok": True, "valid": False, "reason": "not_connected"}
    try:
        if integration == "gmail":
            from src.integrations.gmail import GmailIntegration
            g = GmailIntegration(token=token)
            g.connect()
            valid = g._client is not None
        elif integration == "calendar":
            from src.integrations.calendar import CalendarIntegration
            c = CalendarIntegration(token=token)
            c.connect()
            valid = c._client is not None
        elif integration == "notion":
            from src.integrations.notion import NotionIntegration
            n = NotionIntegration(token=token.get("access_token"))
            n.connect()
            valid = n._client is not None
        elif integration in ("slack", "whatsapp", "email", "webhook"):
            valid = bool(token.get("access_token"))
        else:
            valid = True
        if not valid:
            try:
                from src.core.notifications import notify_user
                await notify_user(tenant_id, user_id, "connection_issue", f"{integration} token invalid", "Connection may need re-authorization.", meta={"integration": integration})
            except Exception:
                pass
            try:
                from src.core.history import record_history
                await record_history(tenant_id, "all", user_id, "system", f"{integration} connection issue", "Connection may need re-authorization.", source=integration, meta={"integration": integration})
            except Exception:
                pass
        return {"ok": True, "valid": valid}
    except Exception as e:
        try:
            from src.core.notifications import notify_user
            await notify_user(tenant_id, user_id, "connection_issue", f"{integration} validation failed", str(e)[:150], meta={"integration": integration})
        except Exception:
            pass
        try:
            from src.core.history import record_history
            await record_history(tenant_id, "all", user_id, "system", f"{integration} connection issue", str(e)[:150], source=integration, meta={"integration": integration})
        except Exception:
            pass
        return {"ok": True, "valid": False, "reason": str(e)}


@router.get("/connections/{integration}/errors")
async def get_connection_errors(
    integration: str,
    tenant_id: str = Query("default"),
    user_id: str = Query("system"),
    limit: int = Query(10, ge=1, le=20),
) -> dict[str, Any]:
    """Return last N error log entries for this connector."""
    if integration not in INTEGRATIONS:
        raise HTTPException(status_code=400, detail=f"Unknown integration: {integration}")
    sl = _sync_log_store()
    await sl.connect()
    errors = await sl.get_errors(tenant_id=tenant_id, user_id=user_id, integration=integration, limit=limit)
    return {"ok": True, "integration": integration, "errors": errors}


# --- OAuth start (redirect to provider) ---

def _base_url() -> str:
    return os.getenv("BASE_URL", "http://localhost:8000").rstrip("/")


@router.get("/connections/oauth/gmail/start")
async def oauth_gmail_start(
    tenant_id: str = Query("default"),
    user_id: str = Query("system"),
    redirect_after: str = Query(""),
) -> RedirectResponse:
    """Redirect to Google OAuth consent. Uses GOOGLE_CLIENT_ID and scopes for Gmail."""
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    if not client_id:
        raise HTTPException(status_code=503, detail="GOOGLE_CLIENT_ID not configured")
    callback = f"{_base_url()}/api/v1/connections/oauth/gmail/callback"
    state = f"{tenant_id}:{user_id}:{redirect_after}" if redirect_after else f"{tenant_id}:{user_id}"
    scope = "https://www.googleapis.com/auth/gmail.readonly https://www.googleapis.com/auth/userinfo.email"
    url = (
        f"https://accounts.google.com/o/oauth2/v2/auth"
        f"?client_id={client_id}&redirect_uri={callback}&response_type=code&scope={scope}&access_type=offline&prompt=consent&state={state}"
    )
    return RedirectResponse(url=url)


@router.get("/connections/oauth/gmail/callback")
async def oauth_gmail_callback(
    code: str,
    state: str = "",
) -> RedirectResponse:
    """Exchange code for tokens and store. Redirect to UI."""
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise HTTPException(status_code=503, detail="Google OAuth not configured")
    import httpx
    callback = f"{_base_url()}/api/v1/connections/oauth/gmail/callback"
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": callback,
                "grant_type": "authorization_code",
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        data = resp.json()
    if "access_token" not in data:
        raise HTTPException(status_code=400, detail=data.get("error_description", "Token exchange failed"))
    parts = (state or "default:system").split(":")
    tenant_id = parts[0] if parts else "default"
    user_id = parts[1] if len(parts) > 1 else "system"
    ts = _token_store()
    await ts.connect()
    await ts.set_token(
        tenant_id=tenant_id,
        user_id=user_id,
        integration="gmail",
        access_token=data["access_token"],
        refresh_token=data.get("refresh_token"),
        expires_at=None,
    )
    front = os.getenv("FRONTEND_URL", "http://localhost:3000").rstrip("/")
    return RedirectResponse(url=f"{front}/connections?gmail=connected")


@router.get("/connections/oauth/calendar/start")
async def oauth_calendar_start(
    tenant_id: str = Query("default"),
    user_id: str = Query("system"),
) -> RedirectResponse:
    """Redirect to Google OAuth for Calendar."""
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    if not client_id:
        raise HTTPException(status_code=503, detail="GOOGLE_CLIENT_ID not configured")
    callback = f"{_base_url()}/api/v1/connections/oauth/calendar/callback"
    state = f"{tenant_id}:{user_id}"
    scope = "https://www.googleapis.com/auth/calendar.readonly https://www.googleapis.com/auth/userinfo.email"
    url = (
        f"https://accounts.google.com/o/oauth2/v2/auth"
        f"?client_id={client_id}&redirect_uri={callback}&response_type=code&scope={scope}&access_type=offline&prompt=consent&state={state}"
    )
    return RedirectResponse(url=url)


@router.get("/connections/oauth/calendar/callback")
async def oauth_calendar_callback(code: str, state: str = "") -> RedirectResponse:
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise HTTPException(status_code=503, detail="Google OAuth not configured")
    import httpx
    callback = f"{_base_url()}/api/v1/connections/oauth/calendar/callback"
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://oauth2.googleapis.com/token",
            data={"code": code, "client_id": client_id, "client_secret": client_secret, "redirect_uri": callback, "grant_type": "authorization_code"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        data = resp.json()
    if "access_token" not in data:
        raise HTTPException(status_code=400, detail=data.get("error_description", "Token exchange failed"))
    parts = (state or "default:system").split(":")
    tenant_id, user_id = parts[0], (parts[1] if len(parts) > 1 else "system")
    ts = _token_store()
    await ts.connect()
    await ts.set_token(tenant_id=tenant_id, user_id=user_id, integration="calendar", access_token=data["access_token"], refresh_token=data.get("refresh_token"))
    front = os.getenv("FRONTEND_URL", "http://localhost:3000").rstrip("/")
    return RedirectResponse(url=f"{front}/connections?calendar=connected")


@router.get("/connections/oauth/slack/start")
async def oauth_slack_start(
    tenant_id: str = Query("default"),
    user_id: str = Query("system"),
) -> RedirectResponse:
    """Redirect to Slack OAuth."""
    client_id = os.getenv("SLACK_CLIENT_ID")
    if not client_id:
        raise HTTPException(status_code=503, detail="SLACK_CLIENT_ID not configured")
    callback = f"{_base_url()}/api/v1/connections/oauth/slack/callback"
    state = f"{tenant_id}:{user_id}"
    scope = "channels:read,chat:write,users:read,groups:read"
    url = f"https://slack.com/oauth/v2/authorize?client_id={client_id}&scope={scope}&redirect_uri={callback}&state={state}"
    return RedirectResponse(url=url)


@router.get("/connections/oauth/slack/callback")
async def oauth_slack_callback(code: str, state: str = "") -> RedirectResponse:
    client_id = os.getenv("SLACK_CLIENT_ID")
    client_secret = os.getenv("SLACK_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise HTTPException(status_code=503, detail="Slack OAuth not configured")
    import httpx
    callback = f"{_base_url()}/api/v1/connections/oauth/slack/callback"
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://slack.com/api/oauth.v2.access",
            data={"code": code, "client_id": client_id, "client_secret": client_secret, "redirect_uri": callback},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        data = resp.json()
    if not data.get("ok") or not data.get("access_token"):
        raise HTTPException(status_code=400, detail=data.get("error", "Token exchange failed"))
    parts = (state or "default:system").split(":")
    tenant_id, user_id = parts[0], (parts[1] if len(parts) > 1 else "system")
    ts = _token_store()
    await ts.connect()
    await ts.set_token(
        tenant_id=tenant_id,
        user_id=user_id,
        integration="slack",
        access_token=data["access_token"],
        extra={"team_id": data.get("team", {}).get("id"), "team_name": data.get("team", {}).get("name")},
    )
    front = os.getenv("FRONTEND_URL", "http://localhost:3000").rstrip("/")
    return RedirectResponse(url=f"{front}/connections?slack=connected")


@router.get("/connections/oauth/notion/start")
async def oauth_notion_start(
    tenant_id: str = Query("default"),
    user_id: str = Query("system"),
) -> RedirectResponse:
    """Redirect to Notion OAuth (if using OAuth app; many use API key instead)."""
    client_id = os.getenv("NOTION_CLIENT_ID")
    if not client_id:
        raise HTTPException(status_code=503, detail="NOTION_CLIENT_ID not configured. For API key, use Connect with token.")
    callback = f"{_base_url()}/api/v1/connections/oauth/notion/callback"
    state = f"{tenant_id}:{user_id}"
    url = f"https://api.notion.com/v1/oauth/authorize?client_id={client_id}&response_type=code&owner=user&redirect_uri={callback}&state={state}"
    return RedirectResponse(url=url)


@router.get("/connections/oauth/notion/callback")
async def oauth_notion_callback(code: str, state: str = "") -> RedirectResponse:
    client_id = os.getenv("NOTION_CLIENT_ID")
    client_secret = os.getenv("NOTION_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise HTTPException(status_code=503, detail="Notion OAuth not configured")
    import base64
    import httpx
    callback = f"{_base_url()}/api/v1/connections/oauth/notion/callback"
    basic = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://api.notion.com/v1/oauth/token",
            json={"grant_type": "authorization_code", "code": code, "redirect_uri": callback},
            headers={"Authorization": f"Basic {basic}", "Content-Type": "application/json"},
        )
        data = resp.json()
    if "access_token" not in data:
        raise HTTPException(status_code=400, detail=data.get("error", "Token exchange failed"))
    parts = (state or "default:system").split(":")
    tenant_id, user_id = parts[0], (parts[1] if len(parts) > 1 else "system")
    ts = _token_store()
    await ts.connect()
    await ts.set_token(tenant_id=tenant_id, user_id=user_id, integration="notion", access_token=data["access_token"])
    front = os.getenv("FRONTEND_URL", "http://localhost:3000").rstrip("/")
    return RedirectResponse(url=f"{front}/connections?notion=connected")
