"use client";

import React, { useState, useCallback, useEffect, Suspense } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { apiClient } from "@/lib/apiClient";
import { useTenantContextStore } from "@/lib/stores/tenantContextStore";
import { PageSkeleton } from "@/components/dashboard/PageSkeleton";
import { ErrorState } from "@/components/feedback/ErrorState";
import { EmptyState } from "@/components/dashboard/EmptyState";

interface GraphNode {
  id: string;
  type: string;
  label: string;
  tenantId: string;
  spaceId?: string;
  metadata?: Record<string, unknown>;
}

interface GraphEdge {
  id: string;
  fromId: string;
  toId: string;
  type: string;
  metadata?: Record<string, unknown>;
}

function GraphContent() {
  const { tenantId, spaceId } = useTenantContextStore();
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Record<string, unknown> | null>(null);
  const [nodes, setNodes] = useState<GraphNode[]>([]);
  const [edges, setEdges] = useState<GraphEdge[]>([]);
  const [loading, setLoading] = useState(false);
  const [loadingGraph, setLoadingGraph] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadGraph = useCallback(async () => {
    setLoadingGraph(true);
    try {
      const res = await apiClient.getGraph({
        tenantId: tenantId ?? "default",
        spaceId: spaceId ?? "all",
      });
      setNodes((res.data?.nodes ?? []) as GraphNode[]);
      setEdges((res.data?.edges ?? []) as GraphEdge[]);
    } catch {
      setNodes([]);
      setEdges([]);
    } finally {
      setLoadingGraph(false);
    }
  }, [tenantId, spaceId]);

  useEffect(() => {
    loadGraph();
  }, [loadGraph]);

  const search = useCallback(async () => {
    if (!query.trim()) return;
    setLoading(true);
    setError(null);
    setResults(null);
    try {
      const res = await apiClient.queryV1({
        tenant_id: tenantId ?? "default",
        space_id: spaceId ?? "all",
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
    <div className="space-y-6" suppressHydrationWarning>
      <div suppressHydrationWarning>
        <h1 className="text-2xl font-bold tracking-tight">Knowledge Graph</h1>
        <p className="text-muted-foreground text-sm mt-1">
          Entities and relationships (nodes/edges) plus RAG search.
        </p>
      </div>
      <Card className="border-neutral-800 bg-neutral-900/70">
        <CardHeader>
          <CardTitle className="text-base">Graph (nodes & edges)</CardTitle>
        </CardHeader>
        <CardContent>
          {loadingGraph ? (
            <div className="flex items-center justify-center py-8">
              <div className="h-6 w-6 animate-spin rounded-full border-2 border-cyan-500 border-t-transparent" />
            </div>
          ) : nodes.length === 0 && edges.length === 0 ? (
            <EmptyState title="No graph data" description="Run the seed script to populate nodes and edges." />
          ) : (
            <div className="space-y-2 text-sm">
              <p className="text-neutral-400"><span className="font-medium text-neutral-200">{nodes.length}</span> nodes, <span className="font-medium text-neutral-200">{edges.length}</span> edges</p>
              <ul className="max-h-48 overflow-auto rounded border border-neutral-800 bg-neutral-950 p-2 text-xs text-neutral-400">
                {nodes.slice(0, 20).map((n) => (
                  <li key={n.id}>{n.type}: {n.label}</li>
                ))}
                {nodes.length > 20 && <li className="text-neutral-500">… and {nodes.length - 20} more</li>}
              </ul>
            </div>
          )}
        </CardContent>
      </Card>
      <Card className="border-neutral-800 bg-neutral-900/70">
        <CardHeader>
          <CardTitle className="text-base">RAG search</CardTitle>
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
      {!loading && results && (
        <Card className="border-neutral-800 bg-neutral-900/70">
          <CardHeader>
            <CardTitle className="text-base">Query result</CardTitle>
          </CardHeader>
          <CardContent>
            <pre className="max-h-96 overflow-auto rounded border border-neutral-800 bg-neutral-950 p-3 text-xs text-neutral-300">
              {JSON.stringify(results, null, 2)}
            </pre>
          </CardContent>
        </Card>
      )}
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
