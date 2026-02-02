"use client";

import { useEffect, useState, useCallback } from "react";
import PostCard from "@/components/brand/PostCard";
import { ErrorState } from "@/components/feedback/ErrorState";
import { apiClient } from "@/lib/apiClient";
import { useTenantContextStore } from "@/lib/stores/tenantContextStore";

interface HistoryEntry {
  id?: string;
  trace_id?: string;
  tenant_id?: string;
  tenantId?: string;
  platform?: string;
  topic_hint?: string;
  topic?: string;
  body_hash?: string;
  published_at?: string;
  timestamp?: string;
  status?: string;
}

function eventToHistoryEntry(ev: Record<string, unknown>): HistoryEntry {
  return {
    id: ev.id as string,
    trace_id: (ev.trace_id ?? ev.id) as string,
    topic_hint: (ev.topic ?? ev.topic_hint) as string,
    platform: (ev.source ?? ev.platform) as string,
    published_at: (ev.timestamp ?? ev.published_at) as string,
    status: (ev.status ?? "delivered") as string,
  };
}

export default function HistoryPage() {
  const { tenantId, spaceId } = useTenantContextStore();
  const [entries, setEntries] = useState<HistoryEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiClient.listHistory({
        tenantId: tenantId ?? "default",
        spaceId: spaceId ?? "all",
      });
      const raw = (res.data ?? []) as Record<string, unknown>[];
      setEntries(raw.map(eventToHistoryEntry));
    } catch {
      setError("Could not load history. Check that the API is reachable.");
    } finally {
      setLoading(false);
    }
  }, [tenantId, spaceId]);

  useEffect(() => {
    load();
  }, [load]);

  if (error) {
    return (
      <div className="space-y-6" suppressHydrationWarning>
        <div suppressHydrationWarning>
          <h1 className="text-2xl font-bold tracking-tight text-neutral-100">History</h1>
          <p className="mt-1 text-sm text-muted-foreground">Past runs from Content Memory Log.</p>
        </div>
        <ErrorState message={error} onRetry={load} />
      </div>
    );
  }

  return (
    <div className="space-y-6" suppressHydrationWarning>
      <div suppressHydrationWarning>
        <h1 className="text-2xl font-bold tracking-tight text-neutral-100">History</h1>
        <p className="mt-1 text-sm text-muted-foreground">Past runs from Content Memory Log.</p>
      </div>
      {loading ? (
        <p className="text-sm text-neutral-400">Loading…</p>
      ) : (
        <>
          <div className="grid gap-4 md:grid-cols-2">
            {entries.map((e, i) => (
              <PostCard
                key={e.trace_id || i}
                headline={e.topic_hint || "Run"}
                body={`Platform: ${e.platform || "-"} · ${e.published_at || ""}`}
                status={e.status}
                trace_id={e.trace_id}
              />
            ))}
          </div>
          {entries.length === 0 && (
            <p className="text-sm text-neutral-400">No history entries. Run the pipeline to populate.</p>
          )}
        </>
      )}
    </div>
  );
}
