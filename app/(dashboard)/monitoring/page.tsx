"use client";

import React, { Suspense, useCallback, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { PageSkeleton } from "@/components/dashboard/PageSkeleton";
import { RunStatsPie } from "@/components/monitoring/RunStatsPie";
import { RunsTable } from "@/components/monitoring/RunsTable";
import { RunDetailModal } from "@/components/monitoring/RunDetailModal";
import {
  getTenantAlertsV1,
  getTenantRunsV1,
  type TenantRunRow,
  type TenantAlertsResponse,
  type TenantRunsResponse,
} from "@/lib/apiClient";
import { useTenantRunsStream } from "@/lib/hooks/useTenantRunsStream";
import { useTenantContextStore } from "@/lib/stores/tenantContextStore";
import { useAuthStore } from "@/lib/stores/authStore";
import { DEFAULT_TENANT_ID } from "@/lib/constants";
import { AlertTriangle, Radio, RefreshCw } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const LIMIT = 20;

type NextActionKind = "failed" | "partial" | "processing" | "completed" | "idle";

type NextAction = {
  action: string;
  outcome: string;
  reason: string;
  confidence: string;
  impact: string;
  resultLabel: string;
  targetRunId: string | null;
  kind: NextActionKind;
};

const IDLE_ACTION: NextAction = {
  action: "Start your next focused move",
  outcome: "You create momentum in your work instead of waiting for urgency.",
  reason: "You have a clear window, so one small move now compounds.",
  confidence: "Based on low-risk current context and no critical pending issues.",
  impact: "Creates forward momentum for your current priorities.",
  resultLabel: "Ready for your next step",
  targetRunId: null,
  kind: "idle",
};

function beforeAfterLabel(kind: NextActionKind): string {
  switch (kind) {
    case "failed":
      return "Blocked flow → Unblocked";
    case "partial":
      return "Incomplete → Completed";
    case "processing":
      return "Drifting → On track";
    case "completed":
      return "New output → Clear next step";
    case "idle":
    default:
      return "Idle → Started momentum";
  }
}

function riskTrustLine(kind: NextActionKind): string {
  switch (kind) {
    case "failed":
      return "Trust: Low risk · Reversible · You stay in control";
    case "partial":
      return "Trust: Safe · Finishes what already started";
    case "processing":
      return "Trust: Low risk · Keeps momentum without side effects";
    case "completed":
      return "Trust: Safe · Review only, no changes yet";
    case "idle":
    default:
      return "Trust: Low risk · Small step, easy to adjust";
  }
}

function hasMeaningfulOutput(row: TenantRunRow): boolean {
  // Heuristic only: richer workflows tend to emit more steps or model-attributed work.
  return row.steps_count >= 8 || Boolean(row.model);
}

function computeNextAction(
  runs: TenantRunRow[],
  actedRunIds: Set<string>,
): NextAction {
  if (!runs.length) return IDLE_ACTION;

  const mk = (
    row: TenantRunRow,
    kind: Exclude<NextActionKind, "idle">,
    action: string,
    outcome: string,
    reason: string,
    confidence: string,
    impact: string,
    resultLabel: string,
  ) => ({ row, kind, action, outcome, reason, confidence, impact, resultLabel });

  const candidates = [
    ...runs
      .filter((r) => r.state === "failed")
      .map((r) =>
        mk(
          r,
          "failed",
          "Fix what is blocking your progress",
          "You restore momentum in your work and get things moving again.",
          "Something important is stuck, and one action now reopens your flow.",
          "Based on the most recent blocked activity and unresolved errors.",
          "This will unblock pending work that cannot move without this fix.",
          "Progress unblocked",
        ),
      ),
    ...runs
      .filter((r) => r.state === "partial")
      .map((r) =>
        mk(
          r,
          "partial",
          "Finish what your work already started",
          "You turn partial progress into a completed outcome.",
          "Most of the effort is already done, so closing now gives the fastest win.",
          "Based on recent activity that advanced but did not fully close.",
          "This completes the last missing part of your current flow.",
          "Flow completed",
        ),
      ),
    ...runs
      .filter((r) => r.state === "processing" || r.state === "accepted")
      .map((r) =>
        mk(
          r,
          "processing",
          "Keep your work moving forward",
          "You maintain momentum and avoid losing focus.",
          "Your active flow is already warm, so continuing now is the easiest path.",
          "Based on live in-progress activity detected in the latest timeline.",
          "This keeps your current workflow on track without extra context switching.",
          "Forward motion secured",
        ),
      ),
    ...runs
      .filter((r) => r.state === "completed" && hasMeaningfulOutput(r))
      .map((r) =>
        mk(
          r,
          "completed",
          "Review the result to unlock your next move",
          "You turn fresh output into a confident next decision.",
          "A meaningful outcome is ready now, and quick review keeps your flow sharp.",
          "Based on a recent completed item with substantial output signals.",
          "This helps you convert new output into immediate follow-up action.",
          "Ready for next step",
        ),
      ),
  ];

  if (!candidates.length) return IDLE_ACTION;

  const basePriority: Record<Exclude<NextActionKind, "idle">, number> = {
    failed: 500,
    partial: 400,
    processing: 300,
    completed: 200,
  };

  // Do not skip acted runs entirely; lower their rank so fresh items win first.
  const scored = candidates
    .map((c, idx) => ({
      ...c,
      score: basePriority[c.kind] - (actedRunIds.has(c.row.run_id) ? 120 : 0) - idx * 0.01,
    }))
    .sort((a, b) => b.score - a.score);

  const top = scored[0];
  return {
    action: top.action,
    outcome: top.outcome,
    reason: top.reason,
    confidence: top.confidence,
    impact: top.impact,
    resultLabel: top.resultLabel,
    targetRunId: top.row.run_id,
    kind: top.kind,
  };
}

function MonitoringContent() {
  const searchParams = useSearchParams();
  const urlTenant = searchParams.get("tenant")?.trim();
  const { tenantId: storeTenant } = useTenantContextStore();
  const { user, loaded } = useAuthStore();
  const skipAuth = process.env.NEXT_PUBLIC_SKIP_AUTH === "1";
  const tenantId =
    urlTenant ||
    (skipAuth
      ? storeTenant || DEFAULT_TENANT_ID
      : user?.tenant_id?.trim() || storeTenant || DEFAULT_TENANT_ID);

  const [payload, setPayload] = useState<TenantRunsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastRefresh, setLastRefresh] = useState<Date | null>(null);
  const [sseLive, setSseLive] = useState(false);
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [alertsPayload, setAlertsPayload] = useState<TenantAlertsResponse | null>(
    null,
  );
  const [actedRunIds, setActedRunIds] = useState<Set<string>>(new Set());
  const [resultState, setResultState] = useState<string | null>(null);
  const [progressFlash, setProgressFlash] = useState<string | null>(null);
  const [recentProgress, setRecentProgress] = useState<string[]>([]);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [data, alerts] = await Promise.all([
        getTenantRunsV1(tenantId, { limit: LIMIT }),
        getTenantAlertsV1(tenantId).catch(() => null),
      ]);
      setPayload(data);
      setAlertsPayload(alerts);
      setLastRefresh(new Date());
    } catch (e) {
      setError(
        e instanceof Error ? e.message : "Failed to load tenant runs",
      );
      setPayload(null);
    } finally {
      setLoading(false);
    }
  }, [tenantId]);

  useEffect(() => {
    if (!skipAuth && !loaded) return;
    if (!skipAuth && !user?.tenant_id && !urlTenant) {
      setLoading(false);
      setError("No tenant in session. Try logging in again.");
      return;
    }
    void load();
  }, [load, skipAuth, loaded, user?.tenant_id, urlTenant]);

  useTenantRunsStream(tenantId, LIMIT, true, (data) => {
    setPayload(data);
    setLastRefresh(new Date());
    setSseLive(true);
  });

  useEffect(() => {
    if (!skipAuth && !loaded) return;
    if (!skipAuth && !user?.tenant_id && !urlTenant) return;
    let cancelled = false;
    const tick = () => {
      void getTenantAlertsV1(tenantId)
        .then((a) => {
          if (!cancelled) setAlertsPayload(a);
        })
        .catch(() => {});
    };
    tick();
    const id = setInterval(tick, 60000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [tenantId, skipAuth, loaded, user?.tenant_id, urlTenant]);

  const onRowClick = (runId: string) => {
    setSelectedRunId(runId);
    setModalOpen(true);
  };

  const runs = useMemo(() => payload?.runs ?? [], [payload?.runs]);
  const stats = payload?.stats ?? {
    total: 0,
    completed: 0,
    partial: 0,
    failed: 0,
  };
  const nextAction = useMemo(
    () => computeNextAction(runs, actedRunIds),
    [runs, actedRunIds],
  );

  const peekNextAction = useMemo(() => {
    const sim = new Set(actedRunIds);
    if (nextAction.targetRunId) sim.add(nextAction.targetRunId);
    return computeNextAction(runs, sim);
  }, [runs, actedRunIds, nextAction]);

  const afterThisLine = useMemo(() => {
    const samePeek =
      nextAction.action === peekNextAction.action &&
      nextAction.kind === peekNextAction.kind &&
      nextAction.targetRunId === peekNextAction.targetRunId;
    if (samePeek) {
      return "After this: The next best move will surface here when it is ready.";
    }
    return `After this: ${peekNextAction.action}`;
  }, [nextAction, peekNextAction]);

  const alertCount = alertsPayload?.count ?? 0;

  if (loading && !payload) {
    return <PageSkeleton title subtitle cards={2} tableRows={6} />;
  }

  const onNextActionClick = () => {
    // Intentional simulation only for interaction testing.
    console.log("[NextAction]", nextAction.kind, nextAction.targetRunId, nextAction.action);
    const ba = beforeAfterLabel(nextAction.kind);
    setProgressFlash(ba);
    setResultState(nextAction.resultLabel);
    const memoryLine = `${ba} — ${nextAction.resultLabel}`;
    setRecentProgress((prev) => [memoryLine, ...prev].slice(0, 3));
    if (nextAction.targetRunId) {
      setActedRunIds((prev) => {
        const next = new Set(prev);
        next.add(nextAction.targetRunId as string);
        return next;
      });
    }
    setTimeout(() => {
      setResultState(null);
      setProgressFlash(null);
    }, 1600);
  };

  return (
    <div className="space-y-6" suppressHydrationWarning>
      <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-textMain flex items-center gap-2 flex-wrap">
            <Radio className="h-6 w-6 text-primary" />
            Run monitor
            {alertCount > 0 ? (
              <span
                className="inline-flex items-center gap-1 rounded-full border border-amber-500/50 bg-amber-500/15 px-2.5 py-0.5 text-xs font-semibold text-amber-200"
                title={alertsPayload?.alerts?.[0]?.message ?? "Active alerts"}
              >
                <AlertTriangle className="h-3.5 w-3.5 shrink-0" />
                {alertCount} alert{alertCount === 1 ? "" : "s"}
              </span>
            ) : null}
          </h1>
          <p className="text-sm text-textSoft mt-1 max-w-2xl">
            Tenant-scoped ingest runs from{" "}
            <code className="rounded bg-surface2 px-1 text-xs">
              GET /api/v1/tenant/{"{"}tenant_id{"}"}/runs
            </code>
            . Query{" "}
            <code className="rounded bg-surface2 px-1 text-xs">
              ?tenant=default
            </code>{" "}
            to override the session tenant. Dev server defaults to{" "}
            <strong className="text-textMain">port 3100</strong> (
            <code className="text-xs">npm run dev</code>
            ).
          </p>
          <p className="text-xs text-textSoft mt-2">
            Tenant:{" "}
            <span className="font-mono text-textMain">{tenantId}</span>
            {lastRefresh && (
              <>
                {" "}
                · Last update: {lastRefresh.toLocaleTimeString()}
                {sseLive ? (
                  <span className="ml-2 text-green-400">· SSE stream</span>
                ) : null}
              </>
            )}
          </p>
        </div>
        <button
          type="button"
          onClick={() => void load()}
          className="inline-flex items-center gap-2 self-start rounded-xl border border-[color:var(--color-border-subtle)] bg-surface2 px-3 py-2 text-sm text-textMain hover:bg-surface2/80"
        >
          <RefreshCw className="h-4 w-4" />
          Refresh
        </button>
      </div>

      {error && (
        <div className="rounded-xl border border-red-500/40 bg-red-500/10 px-4 py-3 text-sm text-red-200">
          {error}
        </div>
      )}

      <Card className="rounded-2xl border-[color:var(--color-border-subtle)] bg-surface1/90">
        <CardHeader>
          <CardTitle className="text-base text-textMain">Next Action</CardTitle>
          <p className="text-xs text-textSoft">
            One recommended move to keep progress clear and continuous.
          </p>
        </CardHeader>
        <CardContent className="space-y-3">
          {resultState ? (
            <div>
              {progressFlash ? (
                <p className="text-sm font-medium text-textMain">{progressFlash}</p>
              ) : null}
              <p className="text-lg font-semibold text-textMain">{resultState}</p>
              <p className="mt-1 text-sm text-textSoft">Preparing your next best move…</p>
            </div>
          ) : (
            <>
              <div>
                <p className="text-lg font-semibold text-textMain">{nextAction.action}</p>
                <p className="mt-1 text-sm text-textSoft">{nextAction.outcome}</p>
              </div>
              <p className="text-xs text-textSoft">{nextAction.impact}</p>
            </>
          )}
          <div>
            <button
              type="button"
              onClick={onNextActionClick}
              disabled={Boolean(resultState)}
              className="inline-flex items-center gap-2 rounded-xl border border-[color:var(--color-border-subtle)] bg-primary px-3 py-2 text-sm font-medium text-white hover:opacity-90"
            >
              {resultState ? "Applying…" : "Continue"}
            </button>
          </div>
          {!resultState ? (
            <div className="space-y-1 border-t border-[color:var(--color-border-subtle)] pt-3">
              <p className="text-[11px] leading-snug text-textSoft">
                Why now: {nextAction.reason}
              </p>
              <p className="text-[11px] leading-snug text-textSoft">
                {riskTrustLine(nextAction.kind)}
              </p>
            </div>
          ) : null}
          {!resultState ? (
            <p className="text-[11px] leading-snug text-textSoft">{afterThisLine}</p>
          ) : null}
          {recentProgress.length > 0 && !resultState ? (
            <div className="border-t border-[color:var(--color-border-subtle)] pt-3">
              <p className="text-[10px] font-medium uppercase tracking-wide text-textSoft">
                Recent progress
              </p>
              <ul className="mt-1.5 space-y-1 text-[11px] text-textSoft">
                {recentProgress.map((line, i) => (
                  <li key={`${line}-${i}`}>{line}</li>
                ))}
              </ul>
            </div>
          ) : null}
        </CardContent>
      </Card>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card className="rounded-2xl border-[color:var(--color-border-subtle)] bg-surface1/90">
          <CardHeader>
            <CardTitle className="text-base text-textMain">
              Page stats (completed / partial / failed)
            </CardTitle>
            <p className="text-xs text-textSoft">
              Counts reflect the current page only (limit {LIMIT}), matching
              the API <code className="text-[11px]">stats</code> object.
            </p>
          </CardHeader>
          <CardContent>
            <RunStatsPie stats={stats} />
            <dl className="mt-4 grid grid-cols-2 gap-2 text-sm sm:grid-cols-4">
              <div>
                <dt className="text-textSoft text-xs">total</dt>
                <dd className="font-semibold text-textMain">{stats.total}</dd>
              </div>
              <div>
                <dt className="text-textSoft text-xs">completed</dt>
                <dd className="font-semibold text-green-400">{stats.completed}</dd>
              </div>
              <div>
                <dt className="text-textSoft text-xs">partial</dt>
                <dd className="font-semibold text-amber-300">{stats.partial}</dd>
              </div>
              <div>
                <dt className="text-textSoft text-xs">failed</dt>
                <dd className="font-semibold text-red-400">{stats.failed}</dd>
              </div>
            </dl>
          </CardContent>
        </Card>

        <Card className="rounded-2xl border-[color:var(--color-border-subtle)] bg-surface1/90">
          <CardHeader>
            <CardTitle className="text-base text-textMain">
              Live updates
            </CardTitle>
            <p className="text-xs text-textSoft">
              Server-Sent Events from{" "}
              <code className="text-[11px]">
                /api/v1/tenant/…/runs/stream
              </code>{" "}
              (15s cadence) with Bearer token from the same storage as other
              API calls. Falls back to manual refresh if the stream fails.
            </p>
          </CardHeader>
          <CardContent>
            <ul className="list-disc space-y-1 pl-4 text-sm text-textSoft">
              <li>Open run details: click a row below.</li>
              <li>Timeline loads from{" "}
                <code className="text-[11px]">/api/v1/run/…/status</code>.
              </li>
            </ul>
          </CardContent>
        </Card>
      </div>

      <Card className="rounded-2xl border-[color:var(--color-border-subtle)] bg-surface1/90">
        <CardHeader>
          <CardTitle className="text-base text-textMain">Recent runs</CardTitle>
        </CardHeader>
        <CardContent>
          <RunsTable
            runs={runs}
            onSelectRun={onRowClick}
            selectedRunId={selectedRunId}
          />
        </CardContent>
      </Card>

      <RunDetailModal
        runId={selectedRunId}
        open={modalOpen}
        onOpenChange={setModalOpen}
      />
    </div>
  );
}

export default function MonitoringPage() {
  return (
    <Suspense fallback={<PageSkeleton title subtitle cards={2} tableRows={6} />}>
      <MonitoringContent />
    </Suspense>
  );
}
