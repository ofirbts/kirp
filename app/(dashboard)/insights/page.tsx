"use client";

import React, { useCallback, useEffect, useState } from "react";
import { apiClient, type InsightV1 } from "@/lib/apiClient";
import { DEFAULT_TENANT_ID } from "@/lib/constants";
import { useTenantContextStore } from "@/lib/stores/tenantContextStore";
import { PageSkeleton } from "@/components/dashboard/PageSkeleton";
import { ErrorState } from "@/components/feedback/ErrorState";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Lightbulb, RefreshCw, Target, BarChart3, Link2, Calendar, Zap } from "lucide-react";

const CATEGORY_ICONS: Record<string, React.ComponentType<{ className?: string }>> = {
  Workload: BarChart3,
  Pattern: BarChart3,
  Commitment: Calendar,
  Connection: Link2,
  Recommendation: Target,
};
const CATEGORY_DEFAULT = Zap;

export default function InsightsPage() {
  const { tenantId, spaceId } = useTenantContextStore();
  const [insights, setInsights] = useState<InsightV1[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<string>("all");

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await apiClient.getInsightsV1({
        tenant_id: tenantId ?? DEFAULT_TENANT_ID,
        space_id: spaceId ?? "all",
        limit: 100,
      });
      setInsights(Array.isArray(data) ? data : []);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load insights");
    } finally {
      setLoading(false);
    }
  }, [tenantId, spaceId]);

  useEffect(() => {
    load();
  }, [load]);

  const filtered =
    filter === "all"
      ? insights
      : insights.filter((i) => i.category.toLowerCase() === filter.toLowerCase());
  const categories = Array.from(new Set(insights.map((i) => i.category))).sort();

  if (loading && insights.length === 0) {
    return <PageSkeleton title subtitle tableRows={8} />;
  }

  if (error) {
    return (
      <div className="space-y-6" suppressHydrationWarning>
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-textMain">Insights</h1>
          <p className="mt-1 text-sm text-textSoft">Real insights from your data.</p>
        </div>
        <ErrorState message={error} onRetry={load} />
      </div>
    );
  }

  return (
    <div className="space-y-6" suppressHydrationWarning>
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-textMain">Insights</h1>
          <p className="mt-1 text-sm text-textSoft">
            Workload, patterns, commitments, connections, and recommendations — from events, tasks, projects, and life areas.
          </p>
        </div>
        <button
          type="button"
          onClick={() => void load()}
          className="inline-flex items-center gap-2 rounded-lg border border-[color:var(--color-border-subtle)] bg-surface2 px-3 py-2 text-sm font-medium text-textMain hover:bg-surface3"
        >
          <RefreshCw className="h-4 w-4" />
          Refresh
        </button>
      </div>

      {insights.length > 0 && (
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => setFilter("all")}
            className={`rounded-full px-4 py-2 text-sm font-medium ${
              filter === "all" ? "bg-primary text-bg" : "bg-surface2 text-textMain hover:bg-surface3"
            }`}
          >
            All ({insights.length})
          </button>
          {categories.map((cat) => (
            <button
              key={cat}
              type="button"
              onClick={() => setFilter(cat)}
              className={`rounded-full px-4 py-2 text-sm font-medium ${
                filter === cat ? "bg-primary text-bg" : "bg-surface2 text-textMain hover:bg-surface3"
              }`}
            >
              {cat}
            </button>
          ))}
        </div>
      )}

      <Card className="rounded-2xl border border-[color:var(--color-border-subtle)] bg-surface1/90 shadow-soft">
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2 text-textMain">
            <Lightbulb className="h-4 w-4 text-amber-400" />
            Your insights
          </CardTitle>
          <p className="text-xs text-textSoft">
            Understanding workload, patterns, commitments, and connections. Recommendations that feel like someone knows you.
          </p>
        </CardHeader>
        <CardContent>
          <ul className="space-y-4">
            {filtered.map((i) => {
              const Icon = CATEGORY_ICONS[i.category] ?? CATEGORY_DEFAULT;
              return (
                <li
                  key={i.id}
                  className="rounded-xl border border-[color:var(--color-border-subtle)] bg-surface2/50 p-4"
                >
                  <div className="flex items-start gap-3">
                    <div className="rounded-lg bg-surface3 p-2">
                      <Icon className="h-4 w-4 text-textMain" />
                    </div>
                    <div className="min-w-0 flex-1">
                      <span className="text-xs font-medium text-primary">{i.category}</span>
                      <h3 className="mt-0.5 font-semibold text-textMain">{i.title}</h3>
                      <p className="mt-2 text-sm text-textSoft whitespace-pre-wrap">{i.body}</p>
                      {i.confidence > 0 && i.confidence < 1 && (
                        <p className="mt-2 text-xs text-textSoft">Confidence: {Math.round(i.confidence * 100)}%</p>
                      )}
                      {i.source_entities?.length > 0 && (
                        <p className="mt-2 text-xs text-textSoft">
                          From: {i.source_entities.map((s) => s.title || s.entity).filter(Boolean).join(", ") || "—"}
                        </p>
                      )}
                    </div>
                  </div>
                </li>
              );
            })}
          </ul>
          {filtered.length === 0 && (
            <p className="py-12 text-center text-sm text-textSoft">
              {insights.length === 0
                ? "No insights yet. Add events, tasks, projects, and commitments to see workload, patterns, and recommendations."
                : `No insights in category "${filter}".`}
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
