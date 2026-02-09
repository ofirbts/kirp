"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { DataTable } from "@/components/dashboard/DataTable";
import { ErrorState } from "@/components/feedback/ErrorState";
import { apiClient } from "@/lib/apiClient";
import { DEFAULT_TENANT_ID } from "@/lib/constants";

interface ContentEntry {
  id?: string;
  trace_id?: string;
  topic_hint?: string;
  platform?: string;
  published_at?: string;
  status?: string;
}

export default function ContentPage() {
  const [entries, setEntries] = useState<ContentEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiClient.listContentIntelligence({
        tenantId: DEFAULT_TENANT_ID,
        spaceId: "all",
      });
      setEntries((res.data ?? []) as ContentEntry[]);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load content");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <div className="space-y-6" suppressHydrationWarning>
      <div suppressHydrationWarning>
        <h1 className="text-2xl font-bold tracking-tight text-neutral-100">Content Intelligence</h1>
        <p className="mt-1 text-sm text-muted-foreground">Generated content. Filter by date, platform, tenant.</p>
      </div>
      {error && <ErrorState message={error} onRetry={load} />}
      <DataTable<ContentEntry>
        title="Content entries"
        data={entries}
        keyExtractor={(r) => r.id ?? r.trace_id ?? `row-${r.topic_hint}-${r.platform}`}
        loading={loading}
        error={error}
        onRetry={load}
        columns={[
          { key: "topic_hint", header: "Topic", render: (r) => r.topic_hint || "—" },
          { key: "platform", header: "Platform", render: (r) => r.platform || "—" },
          { key: "status", header: "Status", render: (r) => r.status || "—" },
          { key: "published_at", header: "Published", render: (r) => r.published_at?.slice(0, 19) ?? "—" },
        ]}
        emptyMessage="No content yet. Run the seed script or pipeline to generate."
        pageSize={10}
      />
      <div>
        <Link href="/mission-control" className="font-medium text-cyan-400 hover:underline">← Mission Control</Link>
      </div>
    </div>
  );
}
