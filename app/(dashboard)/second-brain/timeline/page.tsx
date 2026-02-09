"use client";

import React, { useCallback, useEffect, useState, Suspense } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { PageSkeleton } from "@/components/dashboard/PageSkeleton";
import { ErrorState } from "@/components/feedback/ErrorState";
import { apiClient, type ObligationV1 } from "@/lib/apiClient";
import { DEFAULT_TENANT_ID } from "@/lib/constants";
import { useTenantContextStore } from "@/lib/stores/tenantContextStore";
import { Calendar } from "lucide-react";

function formatDate(s: string | null | undefined): string {
  if (!s) return "—";
  try {
    const d = new Date(s);
    return d.toLocaleDateString(undefined, { dateStyle: "medium", timeZone: "UTC" });
  } catch {
    return String(s);
  }
}

function formatDayKey(s: string | null | undefined): string {
  if (!s) return "";
  return s.slice(0, 10);
}

function TimelineContent() {
  const { tenantId, spaceId } = useTenantContextStore();
  const [obligations, setObligations] = useState<ObligationV1[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiClient.getRemindersUpcoming({
        tenant_id: DEFAULT_TENANT_ID,
        space_id: spaceId ?? "all",
        horizon_days: 14,
      });
      const list = (res.obligations ?? []).slice().sort((a, b) => {
        const da = a.due_date ? new Date(a.due_date).getTime() : 0;
        const db = b.due_date ? new Date(b.due_date).getTime() : 0;
        return da - db;
      });
      setObligations(list);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load timeline");
    } finally {
      setLoading(false);
    }
  }, [tenantId, spaceId]);

  useEffect(() => {
    load();
  }, [load]);

  if (loading) return <PageSkeleton title subtitle tableRows={12} />;
  if (error) {
    return (
      <div className="space-y-6" suppressHydrationWarning>
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-textMain">Timeline</h1>
          <p className="mt-1 text-sm text-textSoft">Obligations and tasks by date.</p>
        </div>
        <ErrorState message={error} onRetry={load} />
      </div>
    );
  }

  const byDay = obligations.reduce<Record<string, ObligationV1[]>>((acc, o) => {
    const key = formatDayKey(o.due_date) || "no-date";
    if (!acc[key]) acc[key] = [];
    acc[key].push(o);
    return acc;
  }, {});
  const sortedDays = Object.keys(byDay).filter((k) => k !== "no-date").sort();
  if (byDay["no-date"]) sortedDays.push("no-date");

  return (
    <div className="space-y-6" suppressHydrationWarning>
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between" suppressHydrationWarning>
        <div suppressHydrationWarning>
          <h1 className="text-2xl font-bold tracking-tight text-textMain flex items-center gap-2">
            <Calendar className="h-7 w-7 text-primary" />
            Timeline
          </h1>
          <p className="mt-1 text-sm text-textSoft">Tasks and commitments over the next 14 days.</p>
        </div>
        <button
          type="button"
          onClick={() => load()}
          className="rounded-full border border-[color:var(--color-border-subtle)] bg-surface2 px-3 py-2 text-xs text-textMain hover:bg-surface3"
        >
          Refresh
        </button>
      </div>

      <Card className="rounded-2xl border border-[color:var(--color-border-subtle)] bg-surface1/90 overflow-hidden shadow-soft">
        <CardHeader>
          <CardTitle className="text-base text-textMain">By date</CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          {sortedDays.length === 0 ? (
            <p className="text-sm text-textSoft py-4">No obligations in the next 14 days.</p>
          ) : (
            sortedDays.map((day) => (
              <div key={day}>
                <h3 className="text-sm font-semibold text-textMain mb-2">
                  {day === "no-date" ? "No due date" : formatDate(day)}
                </h3>
                <ul className="space-y-2 pl-2 border-l-2 border-[color:var(--color-border-subtle)]">
                  {(byDay[day] ?? []).map((o) => (
                    <li key={o.id} className="flex items-start justify-between gap-2 py-1.5 text-sm">
                      <span className="text-textMain">{o.title}</span>
                      <span className="text-[11px] text-textSoft shrink-0 capitalize">{o.entity}</span>
                    </li>
                  ))}
                </ul>
              </div>
            ))
          )}
        </CardContent>
      </Card>
    </div>
  );
}

export default function TimelinePage() {
  return (
    <Suspense fallback={<PageSkeleton title subtitle tableRows={8} />}>
      <TimelineContent />
    </Suspense>
  );
}
