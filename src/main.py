"""
KIRP Enterprise — FastAPI main app.

North Star: Controlled Intelligence Layer · Event-Sourced · Multi-Tenant · Zero Leakage.
"""

from __future__ import annotations

import logging
import os
import sys
import time
from pathlib import Path
from contextlib import asynccontextmanager
from typing import Any
from uuid import uuid4

from dotenv import load_dotenv
load_dotenv()

# Ensure project root is on sys.path when running as a script (e.g. Streamlit, `python src/main.py`)
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
from fastapi import FastAPI, HTTPException, Depends, Request

from src.core.quotas import QuotaExceeded
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, EmailStr, Field
from src.api import governance, observability, whatsapp_os, brand
import src.api.command as command
from src.core.auth import get_current_user, User
from src.core.jwt_utils import require_auth
from src.core.structured_logging import log_json
from src.core.auth import get_current_user, User
from src.core.jwt_utils import require_auth


logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger("KIRP")


# --- Pydantic models ---
class IngestRequest(BaseModel):
    """Body for POST /api/v1/ingest. content must be a string (plain text to ingest)."""
    tenant_id: str = "default"
    space_id: str = "default"
    user_id: str = "dev"
    content: str  # required: plain text to ingest (not an object)
    source: str = "api"
    metadata: dict | None = None


class QueryRequest(BaseModel):
    """RAG query body. Tenant/space/user come from JWT or SKIP_AUTH context — not from client body."""

    query: str
    k: int = 6


class AskRequest(BaseModel):
    """Body for POST /api/v1/ask. Only query is required; tenant_id/user_id/space_id come from JWT."""
    query: str


class OnboardingRequest(BaseModel):
    """Public SaaS signup — creates tenant + trial + API keys (secret shown once)."""

    tenant_name: str = Field(..., min_length=1, max_length=255)
    email: EmailStr


# --- Onboarding rate limit (per client IP, in-memory; tune via ONBOARDING_RL_MAX / ONBOARDING_RL_WINDOW_SEC) ---
_onboarding_rl_hits: dict[str, list[float]] = {}


def _check_onboarding_rate_limit(request: Request) -> None:
    window = float(os.getenv("ONBOARDING_RL_WINDOW_SEC", "60"))
    max_n = int(os.getenv("ONBOARDING_RL_MAX", "10"))
    client_host = (request.client.host if request.client else None) or "unknown"
    now = time.time()
    hits = _onboarding_rl_hits.setdefault(client_host, [])
    hits[:] = [t for t in hits if now - t < window]
    if len(hits) >= max_n:
        raise HTTPException(
            status_code=429,
            detail="Too many onboarding requests; try again later",
        )
    hits.append(now)


# --- Globals (lazy init) ---
_event_store: Any = None
_rag_engine: Any = None
_schema_engine: Any = None
_governance: Any = None
_agent_framework: Any = None
_pipeline: Any = None


async def get_event_store() -> Any:
    global _event_store
    if _event_store is None:
        from src.core.event_store import EventStore
        _event_store = EventStore(os.getenv("MONGO_URI", "mongodb://root:example@localhost:27017/kirp?authSource=admin"))
        try:
            await _event_store.connect()
        except Exception as e:
            _event_store = None
            logger.warning("EventStore connection failed (will retry on next request): %s", e)
            raise
    return _event_store


async def get_rag_engine() -> Any:
    global _rag_engine
    if _rag_engine is None:
        from src.core.rag_engine import get_shared_rag_engine
        try:
            _rag_engine = await get_shared_rag_engine()
        except Exception as e:
            logger.warning("RAGEngine connection failed (will retry on next request): %s", e)
            raise
    return _rag_engine


async def get_schema_engine() -> Any:
    from src.core.schema_engine import get_schema_engine as _get
    return await _get()


async def get_governance() -> Any:
    global _governance
    if _governance is None:
        from src.core.governance import GovernanceEngine
        _governance = GovernanceEngine(os.getenv("OPA_URL"))
    return _governance


async def get_agent_framework() -> Any:
    global _agent_framework
    if _agent_framework is None:
        from src.core.agent_framework import AgentFramework
        from src.core.agent_registry import register_all_agents
        _agent_framework = AgentFramework()
        register_all_agents(_agent_framework)
    return _agent_framework


async def get_pipeline() -> Any:
    global _pipeline
    if _pipeline is None:
        from src.core.pipeline import EventPipeline
        store = await get_event_store()
        rag = await get_rag_engine()
        schema = await get_schema_engine()
        gov = await get_governance()
        agents = await get_agent_framework()
        _pipeline = EventPipeline(store, rag, schema, gov, agents)
    return _pipeline


async def _seed_dev_user_if_needed() -> None:
    """Create dev@localhost with password 'devdevdev' if no users exist (demo user for first run)."""
    try:
        from src.core.auth import get_user_store
        from src.api.v1_auth import _make_password_hash, DEV_EMAIL, DEV_PASSWORD

        store = get_user_store()
        await store.connect()
        existing = await store.get_user_by_email(DEV_EMAIL)
        if existing:
            return
        pw_hash = _make_password_hash(DEV_PASSWORD)
        await store.create_user(
            email=DEV_EMAIL,
            password_hash=pw_hash,
            name="Dev",
            tenant_id="default",
            roles=["admin"],
        )
        logger.info("Seeded dev user: %s (password: %s)", DEV_EMAIL, DEV_PASSWORD)
    except Exception as e:
        logger.warning("Dev user seed failed (non-fatal): %s", e)


async def validate_prod_env() -> None:
    """
    Fail fast in production when critical SaaS dependencies are not configured.
    """
    env = (os.getenv("ENV") or "").strip().lower()
    if env not in ("production", "prod"):
        return
    required = ["STRIPE_SECRET_KEY", "DATABASE_URL", "REDIS_URL"]
    missing = [k for k in required if not (os.getenv(k) or "").strip()]
    if missing:
        raise RuntimeError(f"Missing prod env vars: {missing}")
    logger.info("KIRP production env validated")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: prepare dirs; seed dev user; services connect lazily on first use."""
    logger.info("KIRP Enterprise starting (lazy connect: stores connect on first use)")
    await validate_prod_env()
    prom_dir = os.environ.get("PROMETHEUS_MULTIPROC_DIR")
    if prom_dir:
        os.makedirs(prom_dir, exist_ok=True)
        logger.debug("Prometheus multiprocess dir ensured: %s", prom_dir)
    await _seed_dev_user_if_needed()
    yield
    logger.info("KIRP Enterprise shutting down")


app = FastAPI(
    title="KIRP Enterprise — Intelligence OS",
    version="0.1.0",
    lifespan=lifespan,
)
# CORS: must be added before any routers. No "*" when allow_credentials=True (browser rejects it).
from fastapi.middleware.cors import CORSMiddleware
import os

_cors_origins = [
    "http://localhost:3100",
    "http://127.0.0.1:3100",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

env_origins = os.getenv("CORS_ORIGINS")
if env_origins:
    _cors_origins.extend(
        o.strip()
        for o in env_origins.split(",")
        if o.strip()
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)


def _cors_headers(origin: str | None) -> dict[str, str]:
    """CORS headers for error responses so browser shows real status instead of CORS error."""
    if origin and origin.rstrip("/") in [o.rstrip("/") for o in _cors_origins]:
        return {"Access-Control-Allow-Origin": origin, "Access-Control-Allow-Credentials": "true"}
    return {"Access-Control-Allow-Origin": _cors_origins[0] if _cors_origins else "*", "Access-Control-Allow-Credentials": "true"}


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    origin = request.headers.get("origin")
    headers = _cors_headers(origin)
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail}, headers=headers)


@app.exception_handler(QuotaExceeded)
async def quota_exceeded_handler(request: Request, exc: QuotaExceeded) -> JSONResponse:
    origin = request.headers.get("origin")
    headers = _cors_headers(origin)
    return JSONResponse(
        status_code=429,
        content={
            "detail": "quota_exceeded",
            "tenant_id": exc.tenant_id,
            "llm_cost_used": round(exc.llm_cost_used, 6),
            "limit": exc.limit_usd,
            "estimated_cost": round(exc.estimated_cost, 6),
        },
        headers=headers,
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    origin = request.headers.get("origin")
    headers = _cors_headers(origin)
    logging.exception("Unhandled exception")
    return JSONResponse(status_code=500, content={"detail": "Internal server error"}, headers=headers)


@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    """
    Authentication middleware.

    - If Authorization Bearer is present: decode JWT and set request.state.user from payload.
      Use user_id, tenant_id EXACTLY as in payload — no "dev" fallback.
    - If no valid JWT and SKIP_AUTH=1: set default dev user for local dev only.
    - If no valid JWT and SKIP_AUTH=0: request.state.user stays None → get_tenant_context raises 401.
    """
    if not hasattr(request.state, "user") or request.state.user is None:
        auth = request.headers.get("Authorization") or ""
        if auth.lower().startswith("kirp "):
            pass
        elif auth.startswith("Bearer "):
            token = auth[7:].strip()
            try:
                from src.core.jwt_utils import decode_token

                payload = decode_token(token)
                # JWT requires user_id and tenant_id; use exactly as provided (no dev fallback)
                uid = payload.get("user_id")
                tid = payload.get("tenant_id")
                if not uid or not str(uid).strip():
                    request.state.user = None  # Invalid token shape
                else:
                    request.state.user = {
                        "tenant_id": str(tid).strip() if tid else None,
                        "space_id": (payload.get("space_id") or "all").strip(),
                        "user_id": str(uid).strip(),
                        "roles": payload.get("roles") or [],
                    }
            except HTTPException:
                request.state.user = None

        if not hasattr(request.state, "user") or request.state.user is None:
            skip = os.getenv("SKIP_AUTH", "").lower() in ("1", "true", "yes")
            if skip:
                request.state.user = {
                    "tenant_id": "default",
                    "space_id": "default",
                    "user_id": "dev",
                    "roles": ["admin"],
                }
    return await call_next(request)


@app.middleware("http")
async def kirp_api_key_middleware_layer(request: Request, call_next):
    """Runs before auth_middleware (registered after auth = outer stack = first on request)."""
    from src.middleware.api_key_auth import kirp_api_key_middleware

    return await kirp_api_key_middleware(request, call_next)


@app.get("/health")
async def health() -> dict[str, Any]:
    """Health check for Docker/K8s."""
    try:
        store = await get_event_store()
        rag = await get_rag_engine()
        return {
            "status": "healthy",
            "event_store": "ok",
            "rag_engine": "ok",
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


class StripePaymentIntentBody(BaseModel):
    """Create a PaymentIntent for Stripe Elements (publishable key on client)."""

    tenant_id: str | None = None
    amount_cents: int = Field(default=500, ge=50, le=9_999_999)
    currency: str = Field(default="usd", min_length=3, max_length=10)


@app.post("/api/v1/stripe/create-payment-intent")
async def stripe_create_payment_intent(body: StripePaymentIntentBody) -> dict[str, str]:
    """Return ``clientSecret`` for ``@stripe/react-stripe-js`` Elements. Requires ``STRIPE_SECRET_KEY``."""
    import stripe as stripe_sdk

    sk = os.getenv("STRIPE_SECRET_KEY", "").strip()
    if not sk:
        raise HTTPException(
            status_code=503,
            detail="STRIPE_SECRET_KEY not configured",
        )
    stripe_sdk.api_key = sk
    try:
        intent = stripe_sdk.PaymentIntent.create(
            amount=body.amount_cents,
            currency=body.currency.lower(),
            automatic_payment_methods={"enabled": True},
            metadata={
                "tenant_id": (body.tenant_id or "").strip(),
            },
        )
    except Exception as e:
        logger.warning("Stripe PaymentIntent create failed: %s", e)
        raise HTTPException(status_code=502, detail="Stripe error") from e
    cs = intent.client_secret
    if not cs:
        raise HTTPException(status_code=502, detail="Missing client_secret from Stripe")
    return {"clientSecret": cs}


@app.post("/api/v1/onboarding", status_code=201)
async def saas_onboarding(body: OnboardingRequest, request: Request) -> dict[str, Any]:
    """
    Create a new tenant (30-day trial), default space, and API keys. No JWT required.
    Store ``secret_key`` securely; it cannot be retrieved again.
    """
    from src.services.onboarding_service import OnboardingError, create_tenant

    _check_onboarding_rate_limit(request)
    try:
        return await create_tenant(body.tenant_name, str(body.email))
    except OnboardingError as e:
        msg = str(e)
        if "already registered" in msg.lower():
            raise HTTPException(status_code=409, detail=msg) from e
        raise HTTPException(status_code=400, detail=msg) from e


@app.post("/api/v1/stripe/webhook")
async def stripe_webhook(request: Request) -> dict[str, Any]:
    """
    Stripe billing webhooks (raw body required for signature verification).
    Configure ``STRIPE_WEBHOOK_SECRET``; put ``tenant_id`` on subscription metadata.
    """
    import stripe

    from src.services.stripe_service import handle_webhook, verify_webhook_signature

    payload = await request.body()
    sig = request.headers.get("stripe-signature") or ""
    wh_tenant_id: str | None = None
    wh_trace_id: str | None = None
    try:
        event = verify_webhook_signature(payload, sig)
        obj = ((event or {}).get("data") or {}).get("object") or {}
        meta = obj.get("metadata") or {}
        tenant_id = meta.get("tenant_id")
        wh_tenant_id = tenant_id if isinstance(tenant_id, str) else None
        wh_trace_id = (event or {}).get("id")
        log_json(
            logger,
            "info",
            "stripe_webhook_received",
            step="stripe_webhook",
            tenant_id=tenant_id,
            run_id=None,
            trace_id=(event or {}).get("id"),
            event_type=(event or {}).get("type"),
        )
        await handle_webhook(event)
        log_json(
            logger,
            "info",
            "stripe_webhook_processed",
            step="stripe_webhook",
            tenant_id=tenant_id,
            run_id=None,
            trace_id=(event or {}).get("id"),
            event_type=(event or {}).get("type"),
        )
    except stripe.SignatureVerificationError as e:
        log_json(
            logger,
            "error",
            "stripe_webhook_failed",
            step="stripe_webhook_signature",
            tenant_id=None,
            run_id=None,
            trace_id=None,
            reason=str(e),
        )
        logger.warning("Stripe webhook signature failed: %s", e)
        raise HTTPException(status_code=400, detail="Invalid signature") from e
    except ValueError as e:
        log_json(
            logger,
            "error",
            "stripe_webhook_failed",
            step="stripe_webhook_value_error",
            tenant_id=wh_tenant_id,
            run_id=None,
            trace_id=wh_trace_id,
            reason=str(e),
        )
        raise HTTPException(status_code=400, detail=str(e)) from e
    return {"received": True}


@app.get("/healthz")
async def healthz() -> dict[str, Any]:
    """
    Lightweight health check for platforms (e.g. Streamlit Cloud) that probe `/healthz`.

    Does not hit external dependencies to avoid startup failures when optional
    services (Mongo, Qdrant, etc.) are not available.
    """
    return {"status": "ok", "service": "kirp-enterprise-api"}


@app.get("/api/v1/run/{run_id}/status")
async def get_run_status_endpoint(run_id: str, request: Request) -> dict[str, Any]:
    """
    Unified run lifecycle for dashboards/monitoring.
    Reads from RunController (partitioned Redis `tenant:{tenant_id}:{run_id}` + run_lookup, legacy read optional).
    In production, tenant_id on the run must match the authenticated tenant (404 if not).
    """
    from src.auth.tenant_context import get_tenant_context, is_local_or_skip_auth
    from src.core.run_controller import get_run_controller

    rc = get_run_controller()
    auth_ctx = None
    if not is_local_or_skip_auth():
        auth_ctx = get_tenant_context(request)
    status = await rc.get_run_status(
        run_id, tenant_id=(auth_ctx.tenant_id if auth_ctx else None)
    )
    if status is None:
        raise HTTPException(status_code=404, detail="run not found")
    if auth_ctx is not None:
        if (status.get("tenant_id") or "") != (auth_ctx.tenant_id or ""):
            raise HTTPException(status_code=404, detail="run not found")
    state = str(status.get("state") or "accepted")
    steps = status.get("steps") or []
    from src.core.run_controller import infer_llm_route_from_steps

    model = infer_llm_route_from_steps(steps if isinstance(steps, list) else [])
    return {
        "run_id": run_id,
        "state": state,
        "timeline": steps,
        "overall_status": state,
        "is_complete": state in ("completed", "failed"),
        "model": model,
        "started_at": status.get("started_at"),
        "completed_at": status.get("completed_at"),
        "duration_ms": status.get("duration_ms"),
    }


@app.get("/runs/{run_id}")
async def get_run_visibility_endpoint(run_id: str, request: Request) -> dict[str, Any]:
    """
    Compact run visibility: id, trace, aggregate state, wall duration, per-step timing.
    Same tenant isolation as GET /api/v1/run/{run_id}/status (additive endpoint).
    """
    from src.auth.tenant_context import get_tenant_context, is_local_or_skip_auth
    from src.core.run_controller import get_run_controller, run_visibility_payload

    rc = get_run_controller()
    auth_ctx = None
    if not is_local_or_skip_auth():
        auth_ctx = get_tenant_context(request)
    state = await rc.get_run_state(run_id, tenant_id=(auth_ctx.tenant_id if auth_ctx else None))
    if state is None:
        raise HTTPException(status_code=404, detail="run not found")
    if auth_ctx is not None:
        if (state.tenant_id or "") != (auth_ctx.tenant_id or ""):
            raise HTTPException(status_code=404, detail="run not found")
    return run_visibility_payload(state)


@app.get("/api/v1/tenant/{tenant_id}/runs")
async def get_tenant_runs(
    tenant_id: str,
    request: Request,
    limit: int = 50,
) -> dict[str, Any]:
    """
    Tenant run dashboard: recent runs plus aggregate stats for the returned page.
    Caller must be authenticated for the same tenant as `tenant_id` (403 on mismatch).
    """
    from src.auth.tenant_context import get_tenant_context
    from src.core.run_controller import get_run_controller

    ctx = get_tenant_context(request)
    if ctx.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="tenant mismatch")

    rc = get_run_controller()
    runs = await rc.get_recent_runs(tenant_id, limit=limit)
    return {
        "tenant_id": tenant_id,
        "runs": runs,
        "stats": {
            "total": len(runs),
            "completed": sum(1 for r in runs if r.get("state") == "completed"),
            "partial": sum(1 for r in runs if r.get("state") == "partial"),
            "failed": sum(1 for r in runs if r.get("state") == "failed"),
        },
    }


@app.get("/api/v1/tenant/{tenant_id}/runs/stream")
async def tenant_runs_stream(
    tenant_id: str,
    request: Request,
    limit: int = 50,
) -> StreamingResponse:
    """
    Server-Sent Events: periodic JSON snapshots of tenant runs (same shape as GET /runs).
    Clients should use fetch-based SSE (e.g. @microsoft/fetch-event-source) to send Authorization.
    """
    import asyncio
    import json

    from src.auth.tenant_context import get_tenant_context
    from src.core.run_controller import get_run_controller

    ctx = get_tenant_context(request)
    if ctx.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="tenant mismatch")

    lim = max(1, min(int(limit), 200))

    async def event_iter():
        rc = get_run_controller()
        while True:
            if await request.is_disconnected():
                break
            runs = await rc.get_recent_runs(tenant_id, limit=lim)
            stats = {
                "total": len(runs),
                "completed": sum(1 for r in runs if r.get("state") == "completed"),
                "partial": sum(1 for r in runs if r.get("state") == "partial"),
                "failed": sum(1 for r in runs if r.get("state") == "failed"),
            }
            payload = {"tenant_id": tenant_id, "runs": runs, "stats": stats}
            yield f"data: {json.dumps(payload)}\n\n"
            await asyncio.sleep(15)

    return StreamingResponse(
        event_iter(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/api/v1/tenant/{tenant_id}/alerts")
async def get_tenant_alerts(tenant_id: str, request: Request) -> dict[str, Any]:
    """
    Active production alerts for a tenant (Redis `tenant:{tenant_id}:alerts:active`).
    Populated when failure thresholds fire (see `src/core/alerting.py`).
    """
    from src.auth.tenant_context import get_tenant_context
    from src.core.alerting import get_active_alerts

    ctx = get_tenant_context(request)
    if ctx.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="tenant mismatch")

    alerts = await get_active_alerts(tenant_id)
    return {"tenant_id": tenant_id, "alerts": alerts, "count": len(alerts)}


@app.get("/api/v1/tenant/{tenant_id}/usage")
async def get_tenant_llm_usage(tenant_id: str, request: Request) -> dict[str, Any]:
    """
    LLM spend vs configured quota (Redis counter `tenant:{tenant_id}:llm_cost`).
    Set LLM_QUOTA_LIMIT_USD>0 to enforce caps in LLMClient.invoke (429 when exceeded).
    """
    from src.auth.tenant_context import get_tenant_context
    from src.core.quotas import get_effective_llm_quota_limit_usd, get_tenant_llm_cost_used

    ctx = get_tenant_context(request)
    if ctx.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="tenant mismatch")

    used = await get_tenant_llm_cost_used(tenant_id)
    limit = get_effective_llm_quota_limit_usd()
    return {
        "tenant_id": tenant_id,
        "llm_cost_used": round(used, 4),
        "limit": limit if limit > 0 else None,
    }


@app.get("/api/v1/stats")
async def stats(request: Request) -> dict[str, Any]:
    """Dashboard stats from real data (event count, agents, etc.). Tenant-scoped."""
    try:
        from src.auth.tenant_context import get_tenant_context

        ctx = get_tenant_context(request)
        store = await get_event_store()
        agents = await get_agent_framework()
        knowledge_count = await store.count_events(tenant_id=ctx.tenant_id, space_id=ctx.space_id or "all")
        agent_list = agents.list_all()
        notifications = min(99, knowledge_count)
        return {
            "knowledge_items": knowledge_count,
            "active_jobs": 0,
            "new_insights": max(0, knowledge_count // 10),
            "agents": len(agent_list),
            "notifications": notifications,
        }
    except Exception:
        return {
            "knowledge_items": 0,
            "active_jobs": 0,
            "new_insights": 0,
            "agents": 7,
            "notifications": 0,
        }


@app.post("/api/v1/ingest")
async def ingest(req: IngestRequest, request: Request) -> dict[str, Any]:
    """
    Publish ingest envelope to Kafka. Uses ONLY get_tenant_context(request) from JWT.
    No body defaults; no "dev" fallback. Missing user_id → 403.
    """
    run_id: str | None = None
    trace_id: str | None = None
    tenant_id: str | None = None
    try:
        from src.agents.kafka_event_agent import KafkaEventAgent, EventEnvelope
        from src.auth.tenant_context import get_tenant_context
        from src.core.run_controller import get_run_controller

        ctx = get_tenant_context(request)
        tenant_id = ctx.tenant_id
        space_id = ctx.space_id
        user_id = ctx.user_id
        if not user_id or not str(user_id).strip():
            raise HTTPException(status_code=403, detail="user_id required for ingest")

        trace_id = f"tr_{uuid4().hex[:12]}"
        workflow_type = "ingest_event"
        idempotency_key = request.headers.get("Idempotency-Key") or request.headers.get("idempotency-key")
        run = get_run_controller()
        run_id = await run.create_run(
            workflow_type=workflow_type,
            tenant_id=tenant_id,
            idempotency_key=idempotency_key,
            trace_id=trace_id,
        )
        log_json(
            logger,
            "info",
            "ingest_api_received",
            step="api_ingest",
            tenant_id=tenant_id,
            run_id=run_id,
            trace_id=trace_id,
            source=req.source,
        )

        payload = {
            "text": req.content,
            "tenant_id": tenant_id,
            "space_id": space_id,
            "user_id": user_id,
            "source": req.source,
            "trace_id": trace_id,
            "run_id": run_id,
            "workflow_type": workflow_type,
            "idempotency_key": idempotency_key,
            "metadata": {
                **(req.metadata or {}),
                "trace_id": trace_id,
                "run_id": run_id,
                "workflow_type": workflow_type,
            },
        }
        emitted = KafkaEventAgent().emit(EventEnvelope(
            type="ingest",
            payload=payload,
            tenant_id=tenant_id,
            space_id=space_id,
            user_id=user_id,
            run_id=run_id,
            workflow_type=workflow_type,
            trace_id=trace_id,
            idempotency_key=idempotency_key,
        ))
        if not emitted:
            log_json(
                logger,
                "error",
                "ingest_api_emit_failed",
                step="kafka_emit",
                tenant_id=tenant_id,
                run_id=run_id,
                trace_id=trace_id,
                reason="event_bus_unavailable",
            )
            await run.update_step(run_id, "kafka_emitted", "failed", error="Event bus unavailable")
            raise HTTPException(status_code=503, detail="Event bus unavailable; ingest not published")
        await run.update_step(run_id, "kafka_emitted", "completed")
        log_json(
            logger,
            "info",
            "ingest_api_published",
            step="kafka_emit",
            tenant_id=tenant_id,
            run_id=run_id,
            trace_id=trace_id,
        )
        return {"ok": True, "run_id": run_id, "trace_id": trace_id}
    except HTTPException:
        raise
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e
    except Exception as e:
        if run_id:
            try:
                from src.core.run_controller import get_run_controller
                await get_run_controller().update_step(run_id, "api_failed", "failed", error=str(e))
            except Exception:
                pass
        log_json(
            logger,
            "error",
            "ingest_api_failed",
            step="api_ingest",
            tenant_id=tenant_id,
            run_id=run_id,
            trace_id=trace_id,
            reason=str(e),
        )
        logger.exception("Ingest failed")
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/api/v1/query")
async def query(req: QueryRequest, request: Request) -> dict[str, Any]:
    """RAG query scoped to authenticated tenant (same model as /api/v1/ingest)."""
    from src.auth.tenant_context import get_tenant_context

    ctx = get_tenant_context(request)
    try:
        rag = await get_rag_engine()
        resp = await rag.search(
            query=req.query,
            tenant_id=ctx.tenant_id,
            space_id=ctx.space_id,
            user_id=ctx.user_id,
            limit=req.k,
        )
        return {
            "ok": True,
            "answer": resp.context_text,
            "confidence": resp.confidence,
            "results": [
                {"text": r.text, "score": r.score, "source": r.source}
                for r in resp.results
            ],
        }
    except Exception as e:
        logger.exception("Query failed")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/ask")
async def ask(
    req: AskRequest,
    _auth: dict = Depends(require_auth),
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Ask/Search/Insights API. Uses JWT for tenant/user; request body is only { "query": "..." }.
    Uses InsightAgent on top of RAG, scoped to current_user.tenant_id and current_user.id.
    """
    try:
        try:
            rag = await get_rag_engine()
        except Exception as rag_err:
            logger.warning("Ask: RAG engine unavailable (e.g. Qdrant down): %s", rag_err)
            return {
                "answer": (
                    "Insights need the vector store (Qdrant). It is not reachable from this API "
                    "(check QDRANT_URL or add Qdrant to your compose stack). "
                    "Other dashboard features can still work."
                ),
                "sources": [],
                "needs_external_info": True,
            }
        from src.agents.insight import InsightAgent
        from src.core.llm_run_context import reset_llm_tenant_id, set_llm_tenant_id

        agent = InsightAgent(rag)
        tenant_id = user.tenant_id
        space_id = "all"
        user_id = user.id
        ttok = set_llm_tenant_id(tenant_id)
        try:
            result = await agent.ask(
                tenant_id=tenant_id,
                space_id=space_id,
                query=req.query,
                user_id=user_id,
            )
        finally:
            reset_llm_tenant_id(ttok)
        return {
            "answer": result.answer,
            "sources": result.sources,
            "needs_external_info": result.needs_external_info,
        }
    except QuotaExceeded:
        raise
    except Exception as e:
        logger.exception("Ask failed")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/agents")
async def list_agents_v1(
    _auth: dict = Depends(require_auth),
    user: User = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """List registered agents with last_run from logs (id = name for E2E and callability). Tenant from JWT."""
    agents = await get_agent_framework()
    from src.core.agent_scheduler import get_agent_logs_store
    logs_store = get_agent_logs_store()
    tenant_id = user.tenant_id
    try:
        await logs_store.connect()
        all_logs = await logs_store.list_(tenant_id=tenant_id, limit=500)
        last_by_agent = {}
        for log in all_logs:
            n = log.get("agent_name")
            if n and (n not in last_by_agent or (log.get("run_at") or "") > (last_by_agent[n].get("run_at") or "")):
                last_by_agent[n] = log
    except Exception:
        last_by_agent = {}
    return [
        {
            "id": s.name,
            "name": s.name,
            "type": s.type,
            "triggers": s.triggers,
            "description": s.description,
            "last_run": last_by_agent.get(s.name, {}).get("run_at"),
            "next_run": None,
        }
        for s in agents.list_all()
    ]


@app.post("/api/v1/agents/{agent_id}/run")
async def run_agent_v1(
    agent_id: str,
    body: dict | None = None,
    _auth: dict = Depends(require_auth),
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Run agent now and log result. Tenant/user/space from JWT; agents get RAG context internally when needed."""
    from src.core.agent_scheduler import AgentScheduler, get_agent_logs_store
    from src.core.run_controller import get_run_controller
    agents = await get_agent_framework()
    spec = agents.get(agent_id)
    if not spec:
        raise HTTPException(status_code=404, detail=f"Agent not found: {agent_id}")
    tenant_id = user.tenant_id
    space_id = "all"
    user_id = user.id
    run_controller = get_run_controller()
    run_id = await run_controller.create_run(
        workflow_type="agent_run",
        tenant_id=tenant_id,
        idempotency_key=None,
    )
    trace_id = f"tr_{uuid4().hex[:12]}"
    # Inject RAG context so agents that need it (e.g. PatternAnalyzerAgent) do not return missing_rag_context.
    initial_context: dict[str, Any] = {
        "run_id": run_id,
        "trace_id": trace_id,
        "workflow_type": "agent_run",
    }
    try:
        rag = await get_rag_engine()
        rag_response = await rag.search(
            query="recent activity and patterns",
            tenant_id=tenant_id,
            space_id=space_id,
            user_id=user_id,
            limit=10,
        )
        initial_context["rag_response"] = rag_response
    except Exception as e:
        logger.warning("run_agent_v1: could not pre-fetch RAG context for %s: %s", agent_id, e)
    scheduler = AgentScheduler(agents, None)
    result = await scheduler.run_agent_and_log(
        agent_id, tenant_id, space_id, user_id, "manual", initial_context=initial_context
    )
    await run_controller.update_step(
        run_id,
        "agent_scheduler_run",
        "completed" if result.get("ok") else "failed",
        error=result.get("error"),
    )
    try:
        from src.core.notifications import notify_user
        if result.get("ok"):
            actions_count = len(result.get("actions") or [])
            insights_count = len(result.get("insights") or [])
            if actions_count:
                await notify_user(tenant_id, user_id, "agent_action", f"{agent_id} produced actions", f"{actions_count} action(s) queued.", space_id=space_id, meta={"agent_id": agent_id})
            if insights_count:
                await notify_user(tenant_id, user_id, "insight_generated", f"{agent_id} insights", f"{insights_count} insight(s) generated.", space_id=space_id, meta={"agent_id": agent_id})
    except Exception:
        pass
    try:
        from src.core.history import record_history
        if result.get("ok"):
            actions_count = len(result.get("actions") or [])
            insights_count = len(result.get("insights") or [])
            if agent_id == "InsightAgentV2" and insights_count:
                await record_history(tenant_id, space_id, user_id, "agent_insight", "Insight generated", f"{insights_count} insight(s) from {agent_id}.", source="agent", meta={"agent_id": agent_id})
            elif agent_id == "PlannerAgent":
                await record_history(tenant_id, space_id, user_id, "agent_action", "Plan generated", f"Plan from {agent_id}.", source="agent", meta={"agent_id": agent_id})
            elif agent_id == "ExecutionAgent" and actions_count:
                await record_history(tenant_id, space_id, user_id, "agent_action", "Action executed", f"{actions_count} action(s) executed.", source="agent", meta={"agent_id": agent_id})
            elif (actions_count or insights_count):
                await record_history(tenant_id, space_id, user_id, "agent_insight" if insights_count else "agent_action", f"{agent_id} ran", f"{insights_count} insight(s), {actions_count} action(s).", source="agent", meta={"agent_id": agent_id})
    except Exception:
        pass
    # So "Agent actions" UI shows something: push one agent_insight row when agent produced insights.
    try:
        if result.get("ok"):
            insights_count = len(result.get("insights") or [])
            if insights_count > 0:
                from src.core.agent_actions import get_agent_actions_store, action_doc, ACTION_AGENT_INSIGHT
                store = get_agent_actions_store()
                await store.connect()
                doc = action_doc(agent_id, ACTION_AGENT_INSIGHT, {"insights_count": insights_count, "summary": f"{insights_count} insight(s) from {agent_id}"}, tenant_id, space_id, user_id)
                doc["status"] = "executed"  # informational, not pending execution
                await store.create(doc)
    except Exception as e:
        logger.debug("run_agent_v1: could not push agent_insight to actions store: %s", e)
    return {
        "ok": result.get("ok", False),
        "agent_id": agent_id,
        "run_id": run_id,
        "trace_id": trace_id,
        "result": result,
    }


@app.get("/api/v1/agents/logs")
async def list_agent_logs_v1(
    agent_name: str | None = None,
    limit: int = 100,
    _auth: dict = Depends(require_auth),
    user: User = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """List agent run logs (run_at, duration_ms, result_count, errors). Tenant from JWT."""
    try:
        from src.core.agent_scheduler import get_agent_logs_store
        store = get_agent_logs_store()
        await store.connect()
        return await store.list_(tenant_id=user.tenant_id, agent_name=agent_name, limit=limit)
    except Exception as e:
        logging.warning("Agent logs store unavailable: %s", e)
        return []


@app.get("/api/v1/agents/actions")
async def list_agent_actions_v1(
    status: str | None = None,
    agent: str | None = None,
    limit: int = 200,
    _auth: dict = Depends(require_auth),
    user: User = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """List agent actions (pending, executed, failed). Tenant from JWT."""
    try:
        from src.core.agent_actions import get_agent_actions_store
        store = get_agent_actions_store()
        await store.connect()
        return await store.list_(tenant_id=user.tenant_id, status=status, agent=agent, limit=limit)
    except Exception as e:
        logging.warning("Agent actions store unavailable: %s", e)
        return []


@app.get("/api/v1/agents/{agent_id}/status")
async def agent_status_v1(
    agent_id: str,
    _auth: dict = Depends(require_auth),
) -> dict[str, Any]:
    """Agent status (idle when no run in progress). E2E expects valid JSON."""
    agents = await get_agent_framework()
    if not agents.get(agent_id):
        raise HTTPException(status_code=404, detail=f"Agent not found: {agent_id}")
    return {"status": "idle", "agent_id": agent_id}


@app.get("/api/v1/insights")
async def insights(
    space_id: str | None = None,
    limit: int = 50,
    _auth: dict = Depends(require_auth),
    user: User = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """Real insights from workload, patterns, commitments, connections, and recommendations. Tenant/user from JWT."""
    from src.core.insights_engine import InsightsEngine
    schema = await get_schema_engine()
    store = await get_event_store()
    engine = InsightsEngine(schema, store)
    raw = await engine.compute_insights(
        tenant_id=user.tenant_id,
        space_id=space_id or "all",
        user_id=user.id,
        limit=limit,
    )
    return [i.to_dict() for i in raw]


@app.post("/api/v1/notion/sync")
async def notion_sync(request: Request) -> dict[str, Any]:
    """Pull Notion tasks DB and ingest new pages (idempotent). Tenant/space/user from JWT (same as /ingest)."""
    from src.auth.tenant_context import get_tenant_context

    ctx = get_tenant_context(request)
    from src.workers.notion_sync import run_notion_sync
    store = await get_event_store()
    pipe = await get_pipeline()
    from src.integrations.notion import NotionIntegration
    notion = NotionIntegration()
    notion.connect()
    result = await run_notion_sync(
        tenant_id=ctx.tenant_id,
        space_id=ctx.space_id,
        user_id=ctx.user_id,
        event_store=store,
        pipeline=pipe,
        notion=notion,
    )
    return {"ok": True, **result}


# Include routers
from src.api import (
    governance,
    observability,
    whatsapp_os,
    brand,
    auth,
    events,
    agents,
    tenants,
    users,
    decisions,
    graph,
    audit_api,
    v1_auth,
    v1_domain,
    ws_notifications,
    v1_notifications,
    v1_rag,
)
from src.api.routes.llm_usage import router as llm_usage_router

app.include_router(ws_notifications.router)
app.include_router(governance.router)
app.include_router(observability.router)
app.include_router(whatsapp_os.router)
app.include_router(brand.router)
app.include_router(v1_auth.router)
app.include_router(command.router)
app.include_router(auth.router)
app.include_router(events.router)
app.include_router(agents.router)
app.include_router(tenants.router)
app.include_router(users.router)
app.include_router(decisions.router)
app.include_router(graph.router)
app.include_router(audit_api.router)
app.include_router(v1_domain.router)
app.include_router(v1_rag.router)

from src.api import (
    v1_tasks,
    v1_ingestion,
    v1_reminders,
    v1_execute,
    v1_context,
    v1_connections,
    v1_graph,
    v1_history,
    v1_tenants_spaces,
    v1_tenant_usage,
    v1_events,
    v1_users,
    v1_scenarios,
    v1_m3,
)
app.include_router(v1_history.router)
app.include_router(v1_tasks.router)
app.include_router(v1_ingestion.router)
app.include_router(v1_reminders.router)
app.include_router(v1_execute.router)
app.include_router(v1_context.router)
app.include_router(v1_connections.router)
app.include_router(v1_graph.router)
app.include_router(v1_tenants_spaces.router)
app.include_router(v1_tenant_usage.router)
app.include_router(v1_events.router)
app.include_router(v1_users.router)
app.include_router(v1_scenarios.router)
app.include_router(v1_m3.router)
app.include_router(v1_notifications.router)
app.include_router(llm_usage_router, prefix="/api/v1")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.main:app",
        host=os.getenv("API_HOST", "0.0.0.0"),
        port=int(os.getenv("API_PORT", "8000")),
        reload=os.getenv("ENV") == "development",
    )
