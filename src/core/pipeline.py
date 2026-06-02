"""
Event Pipeline — Ingest → Store → RAG → Governance → Agents → Life Objects.

Single flow: Ingest → Governance check → Store (Mongo) → Embed → Qdrant → Life-object extraction → Schema upsert.
No state mutation without event. Multi-tenant isolated.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4, uuid5

from src.core.event_store import Event, EventStore, Sensitivity
from src.core.life_objects import extract_life_objects
from src.core.structured_logging import log_json
from src.telemetry.orchestration_trace import log_trace
from src.models.schema import SchemaEntity
from src.observability.metrics import MetricsCollector

logger = logging.getLogger(__name__)

_pipeline_metrics = MetricsCollector("kirp_pipeline")


class RunStateMissing(ValueError):
    """Strict pipeline policy: missing run_id, or run_id with no RunController state for tenant."""


class EventPipeline:
    """
    Orchestrates ingest: event store, RAG, governance, agents.
    """

    def __init__(
        self,
        store: EventStore,
        rag: Any,
        schema: Any,
        gov: Any,
        agents: Any,
    ) -> None:
        self._store = store
        self._rag = rag
        self._schema = schema
        self._gov = gov
        self._agents = agents

    async def run(
        self,
        tenant_id: str,
        space_id: str,
        user_id: str,
        source: str,
        content: str,
        metadata: dict | None = None,
        sensitivity: Sensitivity | None = None,
        event_id: UUID | None = None,
        event_type: str = "ingest",
    ) -> UUID:
        """
        Run full pipeline: governance → store → embed → Qdrant → (optional) trigger agents.
        Returns event ID. Pass event_id when re-ingesting from Kafka to preserve id.
        event_type: stored on the event (e.g. "ingest" or "m3.daily_reflection_submitted").

        Env **PIPELINE_RUN_POLICY**: ``warn`` (default) or ``strict``. In ``strict``, a
        ``run_id`` in metadata and matching RunController state are required before work proceeds.
        ``STRICT_RUN_BOUNDARY_FAIL_FAST`` still applies in ``warn`` mode for orphan ``run_id`` only.
        """
        if not tenant_id or tenant_id == "*":
            raise ValueError("tenant_id is required (multi-tenant isolation)")

        _policy_raw = (os.getenv("PIPELINE_RUN_POLICY", "warn") or "warn").strip().lower()
        if _policy_raw not in ("warn", "strict"):
            logger.warning(
                "PIPELINE_RUN_POLICY.invalid policy=%s defaulting to warn",
                _policy_raw,
            )
            _policy_raw = "warn"
        strict_policy = _policy_raw == "strict"

        meta = metadata or {}
        sens = sensitivity or Sensitivity.PRIVATE
        run_id = str(meta.get("run_id")) if meta.get("run_id") else None
        run_controller = None
        if not run_id:
            logger.warning(
                "PIPELINE_NO_RUN_ID tenant_id=%s event_type=%s source=%s",
                tenant_id,
                event_type,
                source,
            )
            _pipeline_metrics.inc(
                "no_run_id_total",
                labels={"event_type": event_type, "source": source},
            )
            if strict_policy:
                raise RunStateMissing("PIPELINE_RUN_ID_REQUIRED")
        else:
            from src.core.run_controller import get_run_controller

            run_controller = get_run_controller()
            state = await run_controller.get_run_state(run_id, tenant_id=tenant_id)
            if state is None:
                logger.error(
                    "PIPELINE_ORPHAN_RUN_ID run_id=%s tenant_id=%s event_type=%s source=%s",
                    run_id,
                    tenant_id,
                    event_type,
                    source,
                )
                _pipeline_metrics.inc(
                    "orphan_run_id_total",
                    labels={"event_type": event_type, "source": source},
                )
                if strict_policy:
                    raise RunStateMissing("PIPELINE_RUN_STATE_MISSING")
                fail_fast = os.getenv("STRICT_RUN_BOUNDARY_FAIL_FAST", "").lower() in (
                    "1",
                    "true",
                    "yes",
                )
                if fail_fast:
                    raise RunStateMissing(
                        "run_missing_state: metadata.run_id present but no RunController state"
                    )
                run_controller = None
            else:
                await run_controller.update_step(run_id, "pipeline_start", "processing")

        # Build context for governance; M3 events get identity_entropy_score and resource_type
        gov_context: dict[str, Any] = {
            "sensitivity": sens.value,
            "resource_type": "event",
            "event_type": event_type,
        }
        if event_type.startswith("m3."):
            from src.modules.m3.ege import compute_identity_entropy_score
            gov_context["module"] = "m3"
            gov_context["identity_entropy_score"] = compute_identity_entropy_score(meta, event_type)
            if "monthly_evolution" in event_type:
                gov_context["resource_type"] = "m3.monthly_evolution"
            elif "weekly_synthesis" in event_type:
                gov_context["resource_type"] = "m3.weekly_synthesis"
            elif "reflection" in event_type:
                gov_context["resource_type"] = "m3.reflection"
            elif "micro_action" in event_type:
                gov_context["resource_type"] = "m3.micro_action"
            elif "identity_vector" in event_type or "gap_analysis" in event_type:
                gov_context["resource_type"] = "m3.identity_trajectory"
            else:
                gov_context["resource_type"] = "m3.event"

        log_trace(
            logger,
            stage="governance_before",
            trace_id=str(meta.get("trace_id") or ""),
            event_id=str(event_id) if event_id is not None else None,
            tenant_id=tenant_id,
            event_type=event_type,
            source=source,
            strict_policy=strict_policy,
        )

        check = await self._gov.check(
            tenant_id=tenant_id,
            space_id=space_id,
            user_id=user_id,
            action="write",
            resource="event",
            context=gov_context,
        )
        log_trace(
            logger,
            stage="governance_after",
            trace_id=str(meta.get("trace_id") or ""),
            event_id=str(event_id) if event_id is not None else None,
            tenant_id=tenant_id,
            event_type=event_type,
            source=source,
            allowed=check.allowed,
            requires_approval=check.requires_approval,
            reason=check.reason,
        )
        try:
            from src.telemetry.execution_shadow import emit_shadow_execution_observation

            emit_shadow_execution_observation(
                trace_id=str(meta.get("trace_id") or ""),
                event_id=str(event_id) if event_id is not None else "",
                tenant_id=tenant_id,
                hook_source="pipeline",
                event_type=event_type,
                source=source,
                governance_allowed=check.allowed,
                governance_requires_approval=check.requires_approval,
                governance_reason=check.reason,
                metadata=meta,
            )
        except Exception as exc:
            logger.warning("shadow_execution_observation_failed trace=%s err=%s", meta.get("trace_id"), exc)

        trace_id_gov = str(meta.get("trace_id") or "").strip()
        if trace_id_gov:
            try:
                from src.telemetry.governed_runtime import (
                    apply_governed_runtime_verdict,
                    build_pipeline_governance_timeline,
                    emit_governed_runtime_trace,
                    evaluate_governed_runtime,
                )

                rt_timeline = build_pipeline_governance_timeline(
                    trace_id=trace_id_gov,
                    tenant_id=tenant_id,
                    event_id=str(event_id) if event_id is not None else None,
                    allowed=check.allowed,
                    event_type=event_type,
                    source=source,
                )
                rt_verdict = evaluate_governed_runtime(rt_timeline, profile="pipeline")
                emit_governed_runtime_trace(
                    logger,
                    rt_verdict,
                    event_id=str(event_id) if event_id is not None else None,
                )
                apply_governed_runtime_verdict(rt_verdict)
            except PermissionError:
                raise
            except Exception as exc:
                logger.warning("governed_runtime_eval_failed trace_id=%s err=%s", trace_id_gov, exc)

        if not check.allowed:
            if run_controller and run_id:
                await run_controller.update_step(run_id, "governance_check", "failed", error=check.reason)
            raise PermissionError(f"Governance denied: {check.reason}")
        if run_controller and run_id:
            await run_controller.update_step(run_id, "governance_check", "completed")
        # M3 human governance (spec 8): when requires_approval, send WhatsApp escalation
        if check.requires_approval and event_type.startswith("m3."):
            try:
                from src.modules.m3.governance import send_m3_whatsapp_escalation
                await send_m3_whatsapp_escalation(
                    tenant_id=tenant_id,
                    space_id=space_id,
                    user_id=user_id,
                    event_type=event_type,
                    reason=check.reason,
                    identity_entropy_score=gov_context.get("identity_entropy_score"),
                    resource_type=gov_context.get("resource_type"),
                    trace_id=str(meta.get("trace_id") or trace_id_gov or ""),
                )
            except Exception as e:
                logger.warning("M3 WhatsApp escalation failed: %s", e)

        event_id = event_id or uuid4()
        trace_id = meta.get("trace_id") or f"tr_{event_id.hex[:8]}"
        log_json(
            logger,
            "info",
            "pipeline_started",
            step="pipeline_start",
            tenant_id=tenant_id,
            run_id=run_id,
            trace_id=trace_id,
            event_type=event_type,
            source=source,
        )

        # Create event (embedding filled below)
        event = Event(
            id=event_id,
            tenant_id=tenant_id,
            space_id=space_id,
            user_id=user_id,
            source=source,
            content=content,
            metadata={**meta, "trace_id": trace_id},
            embedding=[],
            timestamp=datetime.now(timezone.utc),
            sensitivity=sens,
            event_type=event_type,
            trace_id=trace_id,
        )

        # Embed and upsert to Qdrant (best-effort)
        log_trace(
            logger,
            stage="rag_before",
            trace_id=trace_id,
            event_id=str(event_id),
            tenant_id=tenant_id,
            event_type=event_type,
            source=source,
        )
        try:
            emb = await self._rag.embed(content)
            event.embedding = emb
            point_payload: dict[str, Any] = {
                "event_id": str(event_id),
                "content": content,
                "source": source,
                "tenant_id": tenant_id,
                "space_id": space_id,
                "user_id": user_id,
                "timestamp": event.timestamp.isoformat(),
                "trace_id": trace_id,
                "event_type": event_type,
            }
            if event_type.startswith("m3."):
                point_payload["module"] = "m3"
            await self._rag.upsert(
                points=[{
                    "id": str(event_id),
                    "embedding": emb,
                    **point_payload,
                }],
                tenant_id=tenant_id,
                space_id=space_id,
            )
            if run_controller and run_id:
                await run_controller.update_step(run_id, "qdrant_projection", "completed")
        except Exception as e:
            logger.warning("RAG embed/upsert failed (event still stored): %s", e)
            await self._store.write_to_outbox(event_id, tenant_id, "qdrant", str(e))
            if run_controller and run_id:
                await run_controller.update_step(run_id, "qdrant_projection", "failed", error=str(e))

        # Store in Mongo (source of truth)
        log_trace(
            logger,
            stage="mongo_before",
            trace_id=trace_id,
            event_id=str(event_id),
            tenant_id=tenant_id,
            event_type=event_type,
            source=source,
        )
        await self._store.ingest(event)
        if run_controller and run_id:
            await run_controller.update_step(run_id, "mongo_write", "completed")
        logger.info("Pipeline stored event %s tenant=%s trace=%s", event_id, tenant_id, trace_id)

        # History 2.0: human-readable timeline entry by source
        try:
            from src.core.history import record_history
            hist_type = "system"
            title = "Content ingested"
            body = (content[:200] + "…") if len(content) > 200 else content or ""
            if source == "email":
                hist_type = "email_received"
                from_addr = (meta.get("from") or "").strip() or "unknown"
                title = "Email received from " + (from_addr[:60] + "…" if len(from_addr) > 60 else from_addr)
            elif source == "whatsapp":
                hist_type = "whatsapp_message"
                from_addr = (meta.get("from") or meta.get("sender") or "").strip() or "unknown"
                title = "Message from " + (from_addr[:60] + "…" if len(from_addr) > 60 else from_addr)
            elif source == "slack":
                hist_type = "slack_message"
                ch = (meta.get("channel") or meta.get("channel_id") or "").strip() or "channel"
                title = "Slack message in #" + (ch[:40] + "…" if len(ch) > 40 else ch)
            elif source == "calendar":
                hist_type = "calendar_event"
                title = (meta.get("summary") or content.split("\n")[0] if content else "Calendar event")[:80]
                title = "Calendar event: " + (title or "Event")
            elif source == "notion":
                hist_type = "notion_sync"
                title = "Notion page synced"
                body = (content[:150] + "…") if len(content) > 150 else (content or "")
            await record_history(
                tenant_id=tenant_id,
                space_id=space_id,
                user_id=user_id,
                type_=hist_type,
                title=title,
                body=body,
                source=source,
                entity_id=str(event_id),
                meta={"trace_id": trace_id, "event_id": str(event_id)},
            )
            logger.info(
                "[INGEST] history entry written: tenant=%s user=%s type=%s event_id=%s",
                tenant_id, user_id, hist_type, event_id,
            )
            if run_controller and run_id:
                await run_controller.update_step(run_id, "history_write", "completed")
        except Exception as e:
            logger.warning("History record failed after ingest: %s", e)
            if run_controller and run_id:
                await run_controller.update_step(
                    run_id, "history_write_failed", "failed", error=str(e)
                )

        # Life-object extraction → classification + NLP dates → SchemaEngine upsert (Phase 2)
        try:
            # Ensure canonical Life Areas exist (Work, Family, Health, Learning)
            await self._schema.ensure_life_areas(tenant_id, space_id)
            objects = extract_life_objects(
                event.content,
                event_id=str(event_id),
                user_id=user_id,
                source=source,
            )
            for obj in objects:
                entity = obj.get("entity") or SchemaEntity.TASK
                title = (obj.get("title") or "").strip() or "(no title)"
                due_date = obj.get("due_date")
                context = obj.get("context")
                # Stable node_id per event + entity + title for upsert idempotency
                node_id = str(uuid5(event_id, f"{entity.value}:{title}"))
                meta: dict[str, Any] = {
                    "source_event_id": str(event_id),
                    "source": source,
                    "user_id": user_id,
                    **(obj.get("metadata") or {}),
                }
                if context:
                    meta["context"] = context
                # Notion bi-directional: store external_id so we can push updates back
                if source == "notion" and event.metadata:
                    if event.metadata.get("external_id"):
                        meta["notion_page_id"] = event.metadata["external_id"]
                    if event.metadata.get("page_id"):
                        meta.setdefault("notion_page_id", event.metadata["page_id"])
                    if event.metadata.get("last_edited_time"):
                        meta["notion_last_edited_time"] = event.metadata["last_edited_time"]
                # Commitments: due_date, source_event_id, owner (already in meta from extract_life_objects)
                await self._schema.upsert_node(
                    tenant_id=tenant_id,
                    space_id=space_id,
                    entity=entity,
                    title=title,
                    node_id=node_id,
                    due_date=due_date,
                    metadata=meta,
                )
            if run_controller and run_id:
                await run_controller.update_step(run_id, "schema_projection", "completed")
        except Exception as e:
            logger.warning("Life-object extraction/upsert failed (event already stored): %s", e)
            await self._store.write_to_outbox(event_id, tenant_id, "schema", str(e))
            if run_controller and run_id:
                await run_controller.update_step(run_id, "schema_projection", "failed", error=str(e))

        # Optional: one bulk-routed LLM call so run timeline shows llm_call_gemma4 (or route override).
        if run_controller and run_id and os.getenv("INGEST_PIPELINE_LLM_ACK", "").lower() in (
            "1",
            "true",
            "yes",
        ):
            from src.core.llm_run_context import reset_llm_run_id, set_llm_run_id
            from src.core.llm_router import get_llm_for_task

            token = set_llm_run_id(run_id)
            try:
                llm = get_llm_for_task("bulk")
                await llm.invoke("Reply with exactly: OK", max_tokens=16, temperature=0.0)
            finally:
                reset_llm_run_id(token)

        if run_controller and run_id:
            await run_controller.update_step(run_id, "pipeline_start", "completed")
            await run_controller.update_step(run_id, "pipeline_complete", "completed")
        log_json(
            logger,
            "info",
            "pipeline_completed",
            step="pipeline_complete",
            tenant_id=tenant_id,
            run_id=run_id,
            trace_id=trace_id,
            event_type=event_type,
        )

        return event.id

    async def run_post_ingest_for_event(self, event_id: UUID, tenant_id: str) -> bool:
        """
        Re-run embed → Qdrant → life-object extraction → schema upsert for an existing event.
        Used after updating an event (e.g. Notion webhook: update_by_external_id then this).
        Does not write to event store. Returns False if event not found.
        """
        event = await self._store.get_by_id_for_tenant(event_id, tenant_id)
        if not event:
            return False
        tenant_id = event.tenant_id
        space_id = event.space_id
        user_id = event.user_id
        source = event.source
        content = event.content
        trace_id = (event.metadata or {}).get("trace_id", "")

        try:
            emb = await self._rag.embed(content)
            await self._rag.upsert(
                points=[{
                    "id": str(event_id),
                    "embedding": emb,
                    "content": content,
                    "source": source,
                    "tenant_id": tenant_id,
                    "space_id": space_id,
                    "user_id": user_id,
                    "timestamp": event.timestamp.isoformat() if event.timestamp else "",
                    "trace_id": trace_id,
                }],
                tenant_id=tenant_id,
                space_id=space_id,
            )
        except Exception as e:
            logger.warning("RAG embed/upsert failed in run_post_ingest_for_event: %s", e)

        try:
            await self._schema.ensure_life_areas(tenant_id, space_id)
            objects = extract_life_objects(
                content,
                event_id=str(event_id),
                user_id=user_id,
                source=source,
            )
            for obj in objects:
                entity = obj.get("entity") or SchemaEntity.TASK
                title = (obj.get("title") or "").strip() or "(no title)"
                due_date = obj.get("due_date")
                context = obj.get("context")
                node_id = str(uuid5(event_id, f"{entity.value}:{title}"))
                meta: dict[str, Any] = {
                    "source_event_id": str(event_id),
                    "source": source,
                    "user_id": user_id,
                    **(obj.get("metadata") or {}),
                }
                if context:
                    meta["context"] = context
                if source == "notion" and event.metadata:
                    if event.metadata.get("external_id"):
                        meta["notion_page_id"] = event.metadata["external_id"]
                    if event.metadata.get("page_id"):
                        meta.setdefault("notion_page_id", event.metadata["page_id"])
                    if event.metadata.get("last_edited_time"):
                        meta["notion_last_edited_time"] = event.metadata["last_edited_time"]
                await self._schema.upsert_node(
                    tenant_id=tenant_id,
                    space_id=space_id,
                    entity=entity,
                    title=title,
                    node_id=node_id,
                    due_date=due_date,
                    metadata=meta,
                )
        except Exception as e:
            logger.warning("Life-object extraction/upsert failed in run_post_ingest_for_event: %s", e)
        return True

    @staticmethod
    def _last_step_status_map(steps: list[dict[str, Any]]) -> dict[str, str]:
        last: dict[str, str] = {}
        for s in steps:
            name = str(s.get("step", ""))
            if name:
                last[name] = str(s.get("status", "")).lower()
        return last

    async def replay_history_for_event(
        self,
        event: Event,
        run_id: str,
        run_controller: Any,
    ) -> bool:
        """Replay History 2.0 for an existing stored event (used by reconciliation)."""
        try:
            from src.core.history import record_history

            tenant_id = event.tenant_id
            space_id = event.space_id
            user_id = event.user_id
            source = event.source
            content = event.content
            meta = event.metadata or {}
            trace_id = meta.get("trace_id") or event.trace_id or ""
            event_id = event.id

            hist_type = "system"
            title = "Content ingested"
            body = (content[:200] + "…") if len(content) > 200 else content or ""
            if source == "email":
                hist_type = "email_received"
                from_addr = (meta.get("from") or "").strip() or "unknown"
                title = "Email received from " + (from_addr[:60] + "…" if len(from_addr) > 60 else from_addr)
            elif source == "whatsapp":
                hist_type = "whatsapp_message"
                from_addr = (meta.get("from") or meta.get("sender") or "").strip() or "unknown"
                title = "Message from " + (from_addr[:60] + "…" if len(from_addr) > 60 else from_addr)
            elif source == "slack":
                hist_type = "slack_message"
                ch = (meta.get("channel") or meta.get("channel_id") or "").strip() or "channel"
                title = "Slack message in #" + (ch[:40] + "…" if len(ch) > 40 else ch)
            elif source == "calendar":
                hist_type = "calendar_event"
                title = (meta.get("summary") or content.split("\n")[0] if content else "Calendar event")[:80]
                title = "Calendar event: " + (title or "Event")
            elif source == "notion":
                hist_type = "notion_sync"
                title = "Notion page synced"
                body = (content[:150] + "…") if len(content) > 150 else (content or "")

            await record_history(
                tenant_id=tenant_id,
                space_id=space_id,
                user_id=user_id,
                type_=hist_type,
                title=title,
                body=body,
                source=source,
                entity_id=str(event_id),
                meta={"trace_id": trace_id, "event_id": str(event_id)},
            )
            await run_controller.update_step(run_id, "history_write", "completed")
            return True
        except Exception as e:
            logger.warning("replay_history_for_event failed: %s", e)
            await run_controller.update_step(
                run_id, "history_write_failed", "failed", error=str(e)
            )
            return False

    async def reconcile_run(self, run_id: str) -> dict[str, Any]:
        """
        Best-effort repair for aggregate `partial` runs: replay failed history and/or
        Qdrant+schema projections using the canonical Mongo event keyed by metadata.run_id.
        Appends `reconciled` / completed when at least one projection succeeds.
        """
        from src.core.run_controller import get_run_controller

        rc = get_run_controller()
        state = await rc.get_run_state(run_id)
        if state is None:
            return {"run_id": run_id, "skipped": True, "reason": "run_not_found"}
        if state.state != "partial":
            return {"run_id": run_id, "skipped": True, "reason": "not_partial", "state": state.state}

        event = await self._store.find_latest_by_run_id(state.tenant_id, run_id)
        if event is None:
            return {"run_id": run_id, "skipped": True, "reason": "event_not_found"}

        last = self._last_step_status_map(state.steps)
        repaired: list[str] = []
        any_attempt = False

        hist_broken = last.get("history_write_failed") == "failed" or last.get("history_write") == "failed"
        if hist_broken:
            any_attempt = True
            if await self.replay_history_for_event(event, run_id, rc):
                if last.get("history_write_failed") == "failed":
                    await rc.update_step(run_id, "history_write_failed", "completed", error="reconciled")
                repaired.append("history")

        proj_broken = last.get("qdrant_projection") == "failed" or last.get("schema_projection") == "failed"
        if proj_broken:
            any_attempt = True
            if await self.run_post_ingest_for_event(event.id, state.tenant_id):
                await rc.update_step(run_id, "qdrant_projection", "completed")
                await rc.update_step(run_id, "schema_projection", "completed")
                repaired.append("projections")

        if not any_attempt:
            return {"run_id": run_id, "skipped": True, "reason": "nothing_to_repair"}

        final_state: str | None = None
        if repaired:
            await rc.update_step(run_id, "reconciled", "completed")
            fin = await rc.get_run_state(run_id, tenant_id=state.tenant_id)
            final_state = fin.state if fin else None

        return {
            "run_id": run_id,
            "skipped": False,
            "repaired": repaired,
            "state_after": final_state,
        }
