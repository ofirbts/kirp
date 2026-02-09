"use client";

import React, { useState, useCallback, useEffect, Suspense } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { apiClient } from "@/lib/apiClient";
import { DEFAULT_TENANT_ID, DEFAULT_USER_ID } from "@/lib/constants";
import { useTenantContextStore } from "@/lib/stores/tenantContextStore";
import { PageSkeleton } from "@/components/dashboard/PageSkeleton";
import { ErrorState } from "@/components/feedback/ErrorState";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { DataTable } from "@/components/dashboard/DataTable";

interface DecisionRow {
  id: string;
  createdAt: string;
  tenantId: string;
  spaceId?: string;
  agentId: string;
  status: string;
  confidence: number;
  output?: unknown;
}

function DecisionsContent() {
  const { tenantId, spaceId, userId } = useTenantContextStore();
  const [query, setQuery] = useState("");
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [decisions, setDecisions] = useState<DecisionRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [loadingList, setLoadingList] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadDecisions = useCallback(async () => {
    setLoadingList(true);
    try {
      const res = await apiClient.listDecisions({
        tenantId: tenantId ?? DEFAULT_TENANT_ID,
        spaceId: spaceId ?? "all",
      });
      setDecisions((res.data ?? []) as DecisionRow[]);
    } catch {
      setDecisions([]);
    } finally {
      setLoadingList(false);
    }
  }, [tenantId, spaceId]);

  useEffect(() => {
    loadDecisions();
  }, [loadDecisions]);

  const search = useCallback(async () => {
    if (!query.trim()) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const res = await apiClient.queryV1({
        tenant_id: tenantId ?? DEFAULT_TENANT_ID,
        space_id: spaceId ?? "all",
        user_id: userId ?? DEFAULT_USER_ID,
        query: query.trim(),
        k: 6,
      });
      setResult(res as Record<string, unknown>);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Decision exploration failed");
    } finally {
      setLoading(false);
    }
  }, [query, tenantId, spaceId, userId]);

  return (
    <div className="space-y-6" suppressHydrationWarning>
      <div suppressHydrationWarning>
        <h1 className="text-2xl font-bold tracking-tight">Decisions</h1>
        <p className="text-muted-foreground text-sm mt-1">
          Browse decisions and explore via RAG query.
        </p>
      </div>

      <DataTable<DecisionRow>
        title="Decision timeline"
        data={decisions}
        keyExtractor={(r) => r.id}
        loading={loadingList}
        columns={[
          { key: "agentId", header: "Agent", render: (r) => r.agentId },
          { key: "status", header: "Status", render: (r) => r.status },
          { key: "confidence", header: "Confidence", render: (r) => (r.confidence * 100).toFixed(0) + "%" },
          { key: "createdAt", header: "Time", render: (r) => r.createdAt?.slice(0, 19) ?? "—" },
        ]}
        emptyMessage="No decisions yet. Run agents or seed script to populate."
        pageSize={10}
      />

      <Card className="border-neutral-800 bg-neutral-900/70">
        <CardHeader>
          <CardTitle className="text-base">Explore (RAG)</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-neutral-500 mb-3">
            Run a query to explore decision-related context from the RAG pipeline.
          </p>
          <div className="flex flex-wrap items-end gap-3">
            <div className="flex-1 min-w-[200px]">
              <label className="block text-xs font-medium text-neutral-500 mb-1">Query</label>
              <Input
                placeholder="e.g. recent decisions, agent outcomes…"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && search()}
                className="border-neutral-700 bg-neutral-900"
              />
            </div>
            <Button onClick={search} disabled={loading || !query.trim()}>
              {loading ? "Searching…" : "Search"}
            </Button>
          </div>
        </CardContent>
      </Card>

      {error && <ErrorState message={error} onRetry={search} />}

      <div className="grid gap-4 md:grid-cols-2">
        <Card className="border-neutral-800 bg-neutral-900/70">
          <CardHeader>
            <CardTitle className="text-base">Inputs card</CardTitle>
          </CardHeader>
          <CardContent>
            {result ? (
              <pre className="max-h-48 overflow-auto rounded bg-neutral-950 p-2 text-xs text-neutral-400">
                {JSON.stringify(result, null, 2)}
              </pre>
            ) : (
              <EmptyState title="No result" description="Run a query to see inputs." />
            )}
          </CardContent>
        </Card>
        <Card className="border-neutral-800 bg-neutral-900/70">
          <CardHeader>
            <CardTitle className="text-base">Summary card</CardTitle>
          </CardHeader>
          <CardContent>
            {result && typeof result.answer === "string" && (
              <p className="text-sm text-neutral-300">{result.answer}</p>
            )}
            {result && !result.answer && (
              <p className="text-sm text-neutral-500">No summary in response.</p>
            )}
            {!result && (
              <EmptyState title="No result" description="Run a query to see summary." />
            )}
          </CardContent>
        </Card>
      </div>

      <Card className="border-neutral-800 bg-neutral-900/70">
        <CardHeader>
          <CardTitle className="text-base">Explainability panel</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-neutral-500">
            When a dedicated decisions API is available, confidence, trace, and explainability will appear here. Currently using queryV1 response.
          </p>
          {result && Array.isArray(result.results) && result.results.length > 0 && (
            <pre className="mt-2 max-h-40 overflow-auto rounded bg-neutral-950 p-2 text-xs text-neutral-400">
              {JSON.stringify(result.results[0], null, 2)}
            </pre>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

export default function DecisionsPage() {
  return (
    <Suspense fallback={<PageSkeleton title subtitle tableRows={5} />}>
      <DecisionsContent />
    </Suspense>
  );
}
