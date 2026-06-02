"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { StatsCard } from "@/components/ui/stats-card";
import { CodeBlock } from "@/components/ui/code-block";
import { RadialChart } from "@/components/charts/RadialChart";
import { Activity, Database } from "lucide-react";
import { apiClient } from "@/lib/apiClient";

export default function ObservabilityPage() {
  const [health, setHealth] = useState<Record<string, unknown> | null>(null);
  const [metrics, setMetrics] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      apiClient.getObservabilityHealth().catch(() => null),
      apiClient.getMetricsSnapshot().catch(() => null),
    ])
      .then(([h, m]) => {
        setHealth(h ?? null);
        setMetrics(m ?? null);
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load"))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[40vh]">
        <p className="text-sm text-textSoft">Loading observability…</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-2xl border border-destructive/40 bg-destructive/10 p-4 text-destructive">
        <p className="font-medium">Error</p>
        <p className="text-sm mt-1">{error}</p>
      </div>
    );
  }

  const rawServices = health && typeof health === "object" && "services" in health
    ? (health.services as Record<string, { status?: string; latency_ms?: number }>) ?? {}
    : {};
  const radialData = Object.entries(rawServices).map(([name, v]) => ({
    name,
    value: v?.status === "ok" || v?.status === "healthy" ? (typeof v?.latency_ms === "number" ? Math.min(500, Math.round(v.latency_ms)) : 1) : 0,
  })).filter((d) => d.name);

  const namespaceCount = Array.isArray(metrics?.namespaces)
    ? (metrics.namespaces as string[]).length
    : 0;
  const namespaceList = Array.isArray(metrics?.namespaces)
    ? (metrics.namespaces as string[]).join(", ")
    : "";

  return (
    <div className="space-y-6" suppressHydrationWarning>
      <div suppressHydrationWarning>
        <h1 className="text-2xl font-bold tracking-tight text-textMain">Observability</h1>
        <p className="text-sm text-textSoft mt-1">
          Health, metrics snapshot, and monitoring.
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <StatsCard
          title="Backend health"
          value={health?.status ? String(health.status) : "—"}
          icon={Activity}
        />
        <StatsCard
          title="Metrics namespaces"
          value={namespaceCount}
          icon={Database}
          description={namespaceList || undefined}
        />
      </div>

      {radialData.length > 0 && (
        <div className="rounded-2xl border border-[color:var(--color-border-subtle)] bg-surface1/90 p-6 shadow-soft">
          <h3 className="text-sm font-medium text-textMain mb-4">
            Service health (latency / status)
          </h3>
          <RadialChart data={radialData} height={260} />
        </div>
      )}

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Metrics namespaces</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-textSoft">
              {namespaceList || "—"}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Metrics snapshot (GET /observability/metrics/snapshot)</CardTitle>
          </CardHeader>
          <CardContent>
            <CodeBlock
              code={JSON.stringify(metrics ?? {}, null, 2)}
              language="json"
              showLineNumbers
            />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
