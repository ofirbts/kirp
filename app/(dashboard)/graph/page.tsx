"use client";

import React, { useState, useCallback, Suspense } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { apiClient } from "@/lib/apiClient";
import { useTenantContextStore } from "@/lib/stores/tenantContextStore";
import { PageSkeleton } from "@/components/dashboard/PageSkeleton";
import { ErrorState } from "@/components/feedback/ErrorState";
import { EmptyState } from "@/components/dashboard/EmptyState";

function GraphContent() {
  const { tenantId, spaceId } = useTenantContextStore();
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const search = useCallback(async () => {
    if (!query.trim()) return;
    setLoading(true);
    setError(null);
    setResults(null);
    try {
      const res = await apiClient.queryV1({
        tenant_id: tenantId ?? "default",
        space_id: spaceId ?? "default",
        user_id: "dashboard",
        query: query.trim(),
        k: 10,
      });
      setResults(res as Record<string, unknown>);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Search failed");
    } finally {
      setLoading(false);
    }
  }, [query, tenantId, spaceId]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Knowledge Graph</h1>
        <p className="text-muted-foreground text-sm mt-1">
          Explore entities and relationships via node search (queryV1).
        </p>
      </div>
      <Card className="border-neutral-800 bg-neutral-900/70">
        <CardHeader>
          <CardTitle className="text-base">Filters and search</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-wrap items-end gap-3">
          <div className="min-w-[200px] flex-1">
            <label className="mb-1 block text-xs font-medium text-neutral-500">Query</label>
            <Input
              placeholder="Search nodes..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && search()}
              className="border-neutral-700 bg-neutral-900"
            />
          </div>
          <Button onClick={search} disabled={loading || !query.trim()}>
            {loading ? "Searching…" : "Search"}
          </Button>
        </CardContent>
      </Card>
      {error && <ErrorState message={error} onRetry={search} />}
      <Card className="border-neutral-800 bg-neutral-900/70">
        <CardHeader>
          <CardTitle className="text-base">Graph canvas</CardTitle>
        </CardHeader>
        <CardContent>
          {loading && (
            <div className="flex items-center justify-center py-12">
              <div className="h-8 w-8 animate-spin rounded-full border-2 border-cyan-500 border-t-transparent" />
            </div>
          )}
          {!loading && !results && !error && (
            <EmptyState title="Run a search" description="Use the query above to search. Results appear here." />
          )}
          {!loading && results && (
            <div className="space-y-2">
              <p className="text-xs text-neutral-500">Query response:</p>
              <pre className="max-h-96 overflow-auto rounded border border-neutral-800 bg-neutral-950 p-3 text-xs text-neutral-300">
                {JSON.stringify(results, null, 2)}
              </pre>
            </div>
          )}
        </CardContent>
      </Card>
      <Card className="border-neutral-800 bg-neutral-900/70">
        <CardHeader>
          <CardTitle className="text-base">Node inspect</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-neutral-500">
            Select a node from search results to inspect. Using queryV1 for exploration.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}

export default function GraphPage() {
  return (
    <Suspense fallback={<PageSkeleton title subtitle tableRows={5} />}>
      <GraphContent />
    </Suspense>
  );
}
