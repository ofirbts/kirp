"use client";

import React, { useCallback, useEffect, useState, Suspense } from "react";
import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { PageSkeleton } from "@/components/dashboard/PageSkeleton";
import { ErrorState } from "@/components/feedback/ErrorState";
import { apiClient, type ObligationV1 } from "@/lib/apiClient";
import { DEFAULT_TENANT_ID } from "@/lib/constants";
import { useTenantContextStore } from "@/lib/stores/tenantContextStore";
import { Calendar, LayoutGrid, Inbox, Lightbulb, ListChecks, ChevronRight, Sparkles } from "lucide-react";

function formatDate(s: string | null | undefined): string {
  if (!s) return "—";
  try {
    const d = new Date(s);
    return d.toLocaleDateString(undefined, { dateStyle: "short", timeZone: "UTC" });
  } catch {
    return String(s);
  }
}

function SecondBrainContent() {
  const { tenantId, spaceId } = useTenantContextStore();
  const [obligations, setObligations] = useState<ObligationV1[]>([]);
  const [insight, setInsight] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [upcomingRes, askRes] = await Promise.all([
        apiClient.getRemindersUpcoming({ tenant_id: tenantId ?? DEFAULT_TENANT_ID, space_id: spaceId ?? "all", horizon_days: 7 }),
        apiClient.askV1({ query: "What should I focus on today? One short paragraph." }).then((r) => r.answer).catch(() => null),
      ]);
      setObligations(upcomingRes.obligations ?? []);
      setInsight(askRes);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load Second Brain");
    } finally {
      setLoading(false);
    }
  }, [tenantId, spaceId]);

  useEffect(() => { load(); }, [load]);

  if (loading) return <PageSkeleton title subtitle cards={4} tableRows={4} />;
  if (error) {
    return (
      <div className="space-y-6" suppressHydrationWarning>
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-textMain">Second Brain</h1>
          <p className="mt-1 text-sm text-textSoft">Daily briefing, timeline, life areas, and suggestions.</p>
        </div>
        <ErrorState message={error} onRetry={load} />
      </div>
    );
  }

  const today = new Date().toISOString().slice(0, 10);
  const todayObligations = obligations.filter((o) => o.due_date && o.due_date.startsWith(today));
  const upcomingObligations = obligations.slice(0, 8);

  const quickLinks = [
    { label: "Timeline", href: "/second-brain/timeline", icon: Calendar },
    { label: "Life Areas", href: "/second-brain/life-areas", icon: LayoutGrid },
    { label: "Inbox", href: "/second-brain/inbox", icon: Inbox },
    { label: "Suggestions", href: "/second-brain/suggestions", icon: Lightbulb },
    { label: "Tasks", href: "/tasks", icon: ListChecks },
  ];

  return (
    <div className="space-y-6" suppressHydrationWarning>
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between" suppressHydrationWarning>
        <div suppressHydrationWarning>
          <h1 className="text-2xl font-bold tracking-tight text-textMain flex items-center gap-2">
            <Sparkles className="h-7 w-7 text-primary" />
            Second Brain
          </h1>
          <p className="mt-1 text-sm text-textSoft">Daily briefing, timeline, life areas, and suggestions.</p>
        </div>
      </div>

      <Card className="rounded-2xl border border-[color:var(--color-border-subtle)] bg-surface1/90 shadow-soft">
        <CardHeader>
          <CardTitle className="text-base text-textMain">Daily briefing</CardTitle>
          <p className="text-xs text-textSoft mt-0.5">Today&apos;s focus and upcoming obligations.</p>
        </CardHeader>
        <CardContent className="space-y-4">
          {insight && (
            <div className="rounded-xl border border-[color:var(--color-border-subtle)] bg-surface2/80 p-4 text-sm text-textMain">
              <p className="whitespace-pre-wrap">{insight}</p>
            </div>
          )}
          <div>
            <p className="text-xs font-medium text-textSoft mb-2">Due today ({todayObligations.length})</p>
            <ul className="space-y-1.5">
              {todayObligations.length === 0 ? (
                <li className="text-sm text-textSoft">Nothing due today.</li>
              ) : (
                todayObligations.map((o) => (
                  <li key={o.id} className="flex items-center justify-between gap-2 text-sm text-textMain">
                    <span className="truncate">{o.title}</span>
                    <span className="text-[11px] text-textSoft shrink-0">{o.entity}</span>
                  </li>
                ))
              )}
            </ul>
          </div>
          <div>
            <p className="text-xs font-medium text-textSoft mb-2">Upcoming (next 7 days)</p>
            <ul className="space-y-1.5 max-h-32 overflow-auto">
              {upcomingObligations.slice(0, 6).map((o) => (
                <li key={o.id} className="flex items-center justify-between gap-2 text-sm text-textMain">
                  <span className="truncate">{o.title}</span>
                  <span className="text-[11px] text-textSoft shrink-0">{formatDate(o.due_date)}</span>
                </li>
              ))}
              {upcomingObligations.length === 0 && <li className="text-sm text-textSoft">No upcoming obligations.</li>}
            </ul>
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {quickLinks.map(({ label, href, icon: Icon }) => (
          <Link key={href} href={href}>
            <Card className="rounded-2xl border border-[color:var(--color-border-subtle)] bg-surface1/90 shadow-soft hover:shadow-hover transition-all h-full">
              <CardContent className="flex items-center justify-between p-4">
                <div className="flex items-center gap-3">
                  <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary/15 text-primary">
                    <Icon className="h-5 w-5" />
                  </span>
                  <span className="font-medium text-textMain">{label}</span>
                </div>
                <ChevronRight className="h-5 w-5 text-textSoft" />
              </CardContent>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  );
}

export default function SecondBrainPage() {
  return (
    <Suspense fallback={<PageSkeleton title subtitle cards={4} />}>
      <SecondBrainContent />
    </Suspense>
  );
}
