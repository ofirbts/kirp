"use client";

import React, { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { apiClient } from "@/lib/apiClient";
import { DEFAULT_TENANT_ID } from "@/lib/constants";
import { useTenantContextStore } from "@/lib/stores/tenantContextStore";
import { PageSkeleton } from "@/components/dashboard/PageSkeleton";
import { ErrorState } from "@/components/feedback/ErrorState";

interface SignalRow {
  id?: string;
  topic: string;
  relevance: number;
  urgency: string;
  trend: string;
}

export default function SignalsPage() {
  const { tenantId, spaceId } = useTenantContextStore();
  const [items, setItems] = useState<SignalRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiClient.listSignals({
        tenantId: tenantId ?? DEFAULT_TENANT_ID,
        spaceId: spaceId ?? "all",
      });
      setItems((res.data ?? []) as SignalRow[]);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load signals");
    } finally {
      setLoading(false);
    }
  }, [tenantId, spaceId]);

  useEffect(() => {
    load();
  }, [load]);

  if (loading && items.length === 0) {
    return <PageSkeleton title subtitle tableRows={5} />;
  }

  return (
    <div className="space-y-6" suppressHydrationWarning>
      <div suppressHydrationWarning>
        <h1 className="text-2xl font-bold tracking-tight text-neutral-100">
          Signals & World Context
        </h1>
        <p className="mt-1 text-sm text-muted-foreground">
          World context, trends, signals from the API.
        </p>
      </div>
      {error && <ErrorState message={error} onRetry={load} />}
      <table className="w-full border-collapse text-sm">
        <thead>
          <tr className="border-b border-neutral-700">
            <th className="py-2 text-left text-neutral-400">Topic</th>
            <th className="py-2 text-left text-neutral-400">Relevance</th>
            <th className="py-2 text-left text-neutral-400">Urgency</th>
            <th className="py-2 text-left text-neutral-400">Trend</th>
          </tr>
        </thead>
        <tbody>
          {items.map((s, i) => (
            <tr key={s.id ?? i} className="border-b border-neutral-800">
              <td className="py-2 text-neutral-300">{s.topic}</td>
              <td className="py-2 text-neutral-400">{s.relevance}%</td>
              <td className="py-2 text-neutral-400">{s.urgency}</td>
              <td className="py-2 text-neutral-400">{s.trend}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {items.length === 0 && !error && (
        <p className="text-sm text-neutral-500">No signals yet. Run the seed script to populate.</p>
      )}
      <div>
        <Link
          href="/mission-control"
          className="font-medium text-cyan-400 hover:underline"
        >
          ← Mission Control
        </Link>
      </div>
    </div>
  );
}
