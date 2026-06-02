"use client";

import { useCallback, useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { CodeBlock } from "@/components/ui/code-block";
import { StatsCard } from "@/components/ui/stats-card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Activity, RefreshCw, Shield } from "lucide-react";
import { apiClient } from "@/lib/apiClient";

export default function TracesPage() {
  const [health, setHealth] = useState<Record<string, unknown> | null>(null);
  const [traceIds, setTraceIds] = useState<string[]>([]);
  const [selected, setSelected] = useState("demo-trace-1");
  const [baselineId, setBaselineId] = useState("demo-trace-good");
  const [payload, setPayload] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [h, list] = await Promise.all([
        apiClient.getTracesHealthV1(),
        apiClient.listTracesV1(50),
      ]);
      setHealth(h as unknown as Record<string, unknown>);
      setTraceIds(list.trace_ids ?? []);
      if (list.trace_ids?.length && !list.trace_ids.includes(selected)) {
        setSelected(list.trace_ids[0]);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load traces");
    } finally {
      setLoading(false);
    }
  }, [selected]);

  const loadTrace = useCallback(async () => {
    if (!selected.trim()) return;
    setError(null);
    try {
      const data = await apiClient.getTraceV1(selected, {
        includeFull: true,
        baselineTraceId: baselineId.trim() || undefined,
      });
      setPayload(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load trace");
    }
  }, [selected, baselineId]);

  const seedDemo = useCallback(async () => {
    setError(null);
    try {
      await apiClient.seedDevTracesV1(true);
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Seed failed");
    }
  }, [refresh]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  useEffect(() => {
    if (!loading && selected) void loadTrace();
  }, [loading, selected, baselineId, loadTrace]);

  if (loading && !health) {
    return (
      <div className="flex items-center justify-center min-h-[40vh]">
        <p className="text-sm text-textSoft">Loading traces…</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-textMain">Execution traces</h1>
          <p className="text-sm text-textSoft mt-1">
            Replay, drift, orchestration, and governed runtime from the telemetry log.
          </p>
        </div>
        <div className="flex gap-2">
          <Button type="button" variant="outline" size="sm" onClick={() => void refresh()}>
            <RefreshCw className="h-4 w-4 mr-1" />
            Refresh
          </Button>
          <Button type="button" variant="secondary" size="sm" onClick={() => void seedDemo()}>
            Seed demo
          </Button>
        </div>
      </div>

      {error ? (
        <div className="rounded-2xl border border-destructive/40 bg-destructive/10 p-4 text-destructive text-sm">
          {error}
        </div>
      ) : null}

      <div className="grid gap-4 md:grid-cols-3">
        <StatsCard
          title="Telemetry health"
          value={health && typeof health.ok === "boolean" ? (health.ok ? "ok" : "issues") : "—"}
          icon={Activity}
        />
        <StatsCard
          title="Traces in log"
          value={traceIds.length}
          icon={Shield}
        />
        <StatsCard
          title="Runtime mode"
          value={
            health && typeof health.governed_runtime_mode === "string"
              ? String(health.governed_runtime_mode)
              : "—"
          }
          icon={Shield}
        />
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Select trace</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-3 items-end">
          <div className="min-w-[200px] flex-1">
            <label className="text-xs text-textSoft block mb-1">Trace ID</label>
            <Input value={selected} onChange={(e) => setSelected(e.target.value)} list="trace-id-list" />
            <datalist id="trace-id-list">
              {traceIds.map((id) => (
                <option key={id} value={id} />
              ))}
            </datalist>
          </div>
          <div className="min-w-[200px] flex-1">
            <label className="text-xs text-textSoft block mb-1">Baseline trace ID</label>
            <Input value={baselineId} onChange={(e) => setBaselineId(e.target.value)} />
          </div>
          <Button type="button" onClick={() => void loadTrace()}>
            Load full stack
          </Button>
        </CardContent>
      </Card>

      {payload ? (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Trace payload</CardTitle>
          </CardHeader>
          <CardContent>
            <CodeBlock code={JSON.stringify(payload, null, 2)} language="json" />
          </CardContent>
        </Card>
      ) : null}
    </div>
  );
}
