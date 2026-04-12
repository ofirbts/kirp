"use client";

import React, { Suspense, useCallback, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { PageSkeleton } from "@/components/dashboard/PageSkeleton";
import { RunStatsPie } from "@/components/monitoring/RunStatsPie";
import { RunsTable } from "@/components/monitoring/RunsTable";
import { RunDetailModal } from "@/components/monitoring/RunDetailModal";
import {
  getTenantAlertsV1,
  getTenantRunsV1,
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

  if (loading && !payload) {
    return <PageSkeleton title subtitle cards={2} tableRows={6} />;
  }

  const stats = payload?.stats ?? {
    total: 0,
    completed: 0,
    partial: 0,
    failed: 0,
  };
  const runs = payload?.runs ?? [];
  const alertCount = alertsPayload?.count ?? 0;

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
