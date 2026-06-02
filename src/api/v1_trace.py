from __future__ import annotations

from fastapi import APIRouter
from fastapi import HTTPException
from fastapi import Query
from src.telemetry.dev_seed import seed_demo_traces
from src.telemetry.trace_baseline import capture_trace_baseline, trace_baseline_to_dict
from src.telemetry.trace_bundle import build_full_trace_response, build_trace_response
from src.telemetry.trace_health import probe_trace_health, trace_health_to_dict
from src.telemetry.trace_reconstructor import reconstruct_timeline_from_file
from src.telemetry.execution_shadow import build_shadow_execution_response
from src.telemetry.trace_sink import development_env, list_trace_ids_from_file, trace_log_path

router = APIRouter(prefix="/api/v1", tags=["trace"])


@router.post("/traces/dev/seed")
async def seed_dev_traces(reset: bool = Query(default=False)) -> dict[str, object]:
    if not development_env():
        raise HTTPException(status_code=403, detail="dev seed only available in development")
    trace_ids = seed_demo_traces(reset=reset)
    if not trace_ids:
        raise HTTPException(status_code=503, detail="KIRP_TRACE_LOG_PATH not configured")
    return {
        "ok": True,
        "trace_ids": list(trace_ids),
        "log_path": trace_log_path() or None,
        "reset": reset,
    }


@router.get("/traces/health")
async def traces_health() -> dict[str, object]:
    return trace_health_to_dict(probe_trace_health())


@router.get("/traces")
async def list_traces(limit: int = Query(default=50, ge=1, le=500)) -> dict[str, object]:
    log_path = trace_log_path()
    trace_ids = list_trace_ids_from_file(log_path, limit=limit)
    return {
        "log_path": log_path or None,
        "total": len(trace_ids),
        "trace_ids": list(trace_ids),
    }


@router.get("/trace/{trace_id}")
async def get_trace(
    trace_id: str,
    include_graph: bool = Query(default=True),
    include_replay: bool = Query(default=False),
    include_decision_memory: bool = Query(default=False),
    include_policy_drift: bool = Query(default=False),
    include_orchestration: bool = Query(default=False),
    include_governed_runtime: bool = Query(default=False),
    include_full: bool = Query(default=False),
    baseline_fingerprint: str | None = Query(default=None),
    baseline_trace_id: str | None = Query(default=None),
) -> dict[str, object]:
    log_path = trace_log_path()
    if include_full:
        return build_full_trace_response(
            trace_id,
            log_path,
            baseline_fingerprint=baseline_fingerprint,
            baseline_trace_id=baseline_trace_id,
        )
    timeline = reconstruct_timeline_from_file(trace_id, log_path)
    return build_trace_response(
        timeline,
        include_graph=include_graph,
        include_replay=include_replay,
        include_decision_memory=include_decision_memory,
        include_policy_drift=include_policy_drift,
        include_orchestration=include_orchestration,
        include_governed_runtime=include_governed_runtime,
        baseline_fingerprint=baseline_fingerprint,
        baseline_trace_id=baseline_trace_id,
        log_path=log_path,
    )


@router.get("/shadow-execution/{trace_id}")
async def get_shadow_execution(trace_id: str) -> dict[str, object]:
    log_path = trace_log_path()
    if not log_path:
        raise HTTPException(status_code=503, detail="KIRP_TRACE_LOG_PATH not configured")
    return build_shadow_execution_response(trace_id, log_path)


@router.get("/trace/{trace_id}/baseline")
async def get_trace_baseline(trace_id: str) -> dict[str, object]:
    log_path = trace_log_path()
    snapshot = capture_trace_baseline(trace_id, log_path)
    available = list_trace_ids_from_file(log_path, limit=50)
    ready = snapshot.total_stages > 0 and snapshot.orchestration_complete
    if not ready:
        raise HTTPException(
            status_code=404,
            detail={
                "message": "trace not found or incomplete in trace log",
                "trace_id": trace_id,
                "log_path": log_path or None,
                "total_stages": snapshot.total_stages,
                "orchestration_complete": snapshot.orchestration_complete,
                "available_trace_ids": list(available),
            },
        )
    return trace_baseline_to_dict(snapshot, ready=True, available_trace_ids=tuple(available))
