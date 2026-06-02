#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

PR_SCOPES: dict[str, tuple[str, ...]] = {
    "local_dev_smoke": (
        "scripts/run_local_kafka_processor.sh",
        "scripts/staging_tenant_smoke.sh",
        "scripts/staging_tenant_helpers.py",
        "scripts/staging_smoke_url.py",
        "src/auth/tenant_context.py",
        "src/core/integrations.py",
        "src/core/registry.py",
        "src/core/governance.py",
        "tests/test_staging_tenant_isolation.py",
        "tests/test_tenant_context_strict_dev.py",
        "tests/test_registry_degraded_connect.py",
        "tests/test_kafka_bootstrap_local.py",
    ),
    "telemetry": (
        "src/telemetry/",
        "src/api/v1_trace.py",
        "app/(dashboard)/traces/",
        "scripts/telemetry_smoke.sh",
        "tests/test_v1_trace_api.py",
        "tests/test_telemetry_",
        "tests/test_execution_shadow.py",
        "tests/test_trace_",
        "tests/test_governed_runtime",
        "tests/test_replay_",
        "tests/test_decision_memory",
        "tests/test_policy_intelligence",
        "tests/test_deterministic_orchestration",
        "tests/test_telemetry_smoke_integration.py",
    ),
    "governance_hardening": (
        "src/core/execution_engine.py",
        "src/core/governance.py",
        "src/core/governance_bundles.py",
        "src/core/pending_executions.py",
        "src/core/whatsapp_outbound.py",
        "src/api/v1_execute.py",
        "tests/test_execution_governance.py",
        "tests/test_whatsapp_outbound.py",
        "tests/test_pending_idempotency.py",
        "tests/test_governance_production.py",
        "tests/test_validate_prod_env.py",
    ),
    "tenant_isolation": (
        "src/core/event_store.py",
        "src/control_plane/access.py",
        "src/core/webhook_tenant.py",
        "src/api/v1_ingestion.py",
        "scripts/tenant_isolation_gate.py",
        "tests/test_api_ingestion_tenant_security.py",
        "tests/test_api_query_security.py",
        "tests/test_api_v1_context_security.py",
        "tests/test_api_v1_rag_tenant_body.py",
        "tests/test_webhook_tenant.py",
        "tests/test_api_notion_sync_security.py",
    ),
    "m3_execution": (
        "src/modules/m3/governance.py",
        "src/modules/m3/handlers.py",
        "src/modules/m3/memory_mongo.py",
        "src/core/pipeline.py",
        "src/core/pipeline_factory.py",
        "tests/test_m3_governance_escalation.py",
        "tests/test_pipeline_",
    ),
    "trace_reconstruction": (
        "src/core/embedding_provider.py",
        "src/core/rag_engine.py",
        "src/workers/kafka_processor.py",
        "src/core/event_store.py",
        "requirements.txt",
        "tests/test_embedding_provider.py",
        "tests/test_rag_engine_qdrant.py",
        "tests/test_kafka_processor_retry.py",
    ),
}

MAX_FILES_PER_PR = 15


def _git_changed_paths() -> list[str]:
    out = subprocess.check_output(
        ["git", "status", "--porcelain"],
        cwd=ROOT,
        text=True,
    )
    paths: list[str] = []
    for line in out.splitlines():
        if not line.strip():
            continue
        path = line[3:].strip()
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        paths.append(path)
    return paths


def _match_scope(path: str, scope: str) -> bool:
    for prefix in PR_SCOPES[scope]:
        if prefix.endswith("/"):
            if path.startswith(prefix):
                return True
        elif prefix.endswith("_"):
            name = Path(path).name
            if name.startswith(prefix.rstrip("_")) or name.startswith(prefix.split("/")[-1].rstrip("_")):
                return True
            if path.startswith(prefix):
                return True
        elif path == prefix or path.startswith(prefix + "/"):
            return True
    return False


def classify(path: str) -> list[str]:
    hits = [scope for scope in PR_SCOPES if _match_scope(path, scope)]
    return hits


def main() -> int:
    changed = _git_changed_paths()
    if not changed:
        print("pr_split_manifest: no changed files")
        return 0

    by_scope: dict[str, list[str]] = {k: [] for k in PR_SCOPES}
    unscoped: list[str] = []
    multi: list[tuple[str, list[str]]] = []

    for path in changed:
        hits = classify(path)
        if not hits:
            unscoped.append(path)
        elif len(hits) > 1:
            multi.append((path, hits))
            for h in hits:
                by_scope[h].append(path)
        else:
            by_scope[hits[0]].append(path)

    print("pr_split_manifest: changed files by intended PR")
    for scope, files in by_scope.items():
        if not files:
            continue
        print(f"\n[{scope}] ({len(files)} files)")
        for f in sorted(files):
            print(f"  {f}")
        if len(files) > MAX_FILES_PER_PR:
            print(f"  WARN: exceeds max {MAX_FILES_PER_PR} for one PR")

    if unscoped:
        print(f"\n[unscoped] ({len(unscoped)} files)")
        for f in sorted(unscoped):
            print(f"  {f}")

    if multi:
        print(f"\n[overlap] ({len(multi)} files in multiple scopes)")
        for path, hits in sorted(multi):
            print(f"  {path}: {', '.join(hits)}")

    total = len(changed)
    print(f"\nTotal changed: {total}")
    if total > MAX_FILES_PER_PR:
        print(f"WARN: WIP {total} files exceeds single-PR limit ({MAX_FILES_PER_PR})")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
