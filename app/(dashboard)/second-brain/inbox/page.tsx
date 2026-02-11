"use client";

import React, { useCallback, useEffect, useState, Suspense } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { PageSkeleton } from "@/components/dashboard/PageSkeleton";
import { ErrorState } from "@/components/feedback/ErrorState";
import { apiClient } from "@/lib/apiClient";
import { DEFAULT_TENANT_ID } from "@/lib/constants";
import { useTenantContextStore } from "@/lib/stores/tenantContextStore";
import { Inbox } from "lucide-react";

interface InboxEvent {
  id: string;
  topic?: string;
  source?: string;
  timestamp?: string;
  payloadPreview?: string;
}

/** First ~3 words or 50 chars for snippet column. */
function snippet(preview: string | undefined, topic: string | undefined): string {
  const raw = (preview || topic || "").trim();
  if (!raw) return "—";
  const words = raw.split(/\s+/).filter(Boolean).slice(0, 3);
  const s = words.join(" ");
  return s.length > 50 ? s.slice(0, 47) + "…" : s || "—";
}

function InboxContent() {
  const { tenantId, spaceId } = useTenantContextStore();
  const [events, setEvents] = useState<InboxEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiClient.listEvents({
        tenantId: tenantId ?? DEFAULT_TENANT_ID,
        spaceId: spaceId ?? "all",
      });
      const raw = ((res.data ?? []) as InboxEvent[]).slice(0, 50);
      raw.sort((a, b) => {
        const at = (a as unknown as { timestamp?: string }).timestamp;
        const bt = (b as unknown as { timestamp?: string }).timestamp;
        const ta = at ? new Date(at).getTime() : 0;
        const tb = bt ? new Date(bt).getTime() : 0;
        return tb - ta;
      });
      const list = raw.map((e) => {
        const o = e as unknown as { timestamp?: string; payloadPreview?: string };
        return {
          ...e,
          timestamp: e.timestamp ?? o.timestamp,
          payloadPreview: e.payloadPreview ?? o.payloadPreview,
        };
      });
      setEvents(list);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load inbox");
    } finally {
      setLoading(false);
    }
  }, [tenantId, spaceId]);

  useEffect(() => { load(); }, [load]);

  if (loading) return <PageSkeleton title subtitle tableRows={10} />;
  if (error) {
    return (
      <div className="space-y-6" suppressHydrationWarning>
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-textMain">Inbox</h1>
          <p className="mt-1 text-sm text-textSoft">Recent activity and ingested items.</p>
        </div>
        <ErrorState message={error} onRetry={load} />
      </div>
    );
  }

  return (
    <div className="space-y-6" suppressHydrationWarning>
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between" suppressHydrationWarning>
        <div suppressHydrationWarning>
          <h1 className="text-2xl font-bold tracking-tight text-textMain flex items-center gap-2">
            <Inbox className="h-7 w-7 text-primary" />
            Inbox
          </h1>
          <p className="mt-1 text-sm text-textSoft">Recent activity and ingested items.</p>
        </div>
        <button type="button" onClick={() => load()} className="rounded-full border border-[color:var(--color-border-subtle)] bg-surface2 px-3 py-2 text-xs text-textMain hover:bg-surface3">
          Refresh
        </button>
      </div>

      <Card className="rounded-2xl border border-[color:var(--color-border-subtle)] bg-surface1/90 overflow-hidden shadow-soft">
        <CardHeader>
          <CardTitle className="text-base text-textMain">Recent events</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full text-sm text-left">
              <thead className="border-b border-[color:var(--color-border-subtle)] bg-surface2 text-textSoft">
                <tr>
                  <th className="px-4 py-3 font-medium">Topic / Source</th>
                  <th className="px-4 py-3 font-medium">Snippet</th>
                  <th className="px-4 py-3 font-medium">Time</th>
                  <th className="px-4 py-3 font-medium">Source</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[color:var(--color-border-subtle)]">
                {events.map((e) => (
                  <tr key={e.id} className="hover:bg-surface2/70">
                    <td className="px-4 py-3 text-textMain">{e.topic || e.source || "—"}</td>
                    <td className="px-4 py-3 text-textSoft max-w-[180px] truncate" title={e.payloadPreview || e.topic || ""}>
                      {snippet(e.payloadPreview, e.topic)}
                    </td>
                    <td className="px-4 py-3 text-textSoft">{e.timestamp ? new Date(e.timestamp).toLocaleString() : "—"}</td>
                    <td className="px-4 py-3 text-textSoft">{e.source ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {events.length === 0 && (
            <div className="px-4 py-8 text-center text-sm text-textSoft">No recent events. Ingest content to see it here.</div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

export default function InboxPage() {
  return (
    <Suspense fallback={<PageSkeleton title subtitle tableRows={8} />}>
      <InboxContent />
    </Suspense>
  );
}
