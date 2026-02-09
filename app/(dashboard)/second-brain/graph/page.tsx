"use client";

import React, { useCallback, useEffect, useRef, useState } from "react";
import dynamic from "next/dynamic";
import { apiClient, type GraphNodeV1, type GraphEdgeV1 } from "@/lib/apiClient";
import { DEFAULT_TENANT_ID } from "@/lib/constants";
import { useTenantContextStore } from "@/lib/stores/tenantContextStore";
import { PageSkeleton } from "@/components/dashboard/PageSkeleton";
import { ErrorState } from "@/components/feedback/ErrorState";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Share2, RefreshCw, Filter, ZoomIn, ZoomOut } from "lucide-react";

// Force graph: task=blue, project=purple, commitment=red, life_area=green, event=gray, person=yellow, source=teal, due_date=slate
const NODE_COLORS: Record<string, string> = {
  task: "#3b82f6",
  project: "#a855f7",
  commitment: "#ef4444",
  life_area: "#22c55e",
  event: "#6b7280",
  person: "#eab308",
  source: "#14b8a6",
  due_date: "#64748b",
};

// Use the dedicated 2D build to avoid pulling in VR/AFRAME dependencies that
// break in the browser when AFRAME is not globally available.
const ForceGraph2D = dynamic(
  () => import("react-force-graph-2d").then((mod) => mod.default),
  { ssr: false, loading: () => <div className="flex h-[500px] items-center justify-center text-textSoft">Loading graph…</div> }
);

type GraphData = { nodes: GraphNodeV1[]; links: { source: string; target: string; type?: string }[] };

function buildGraphData(nodes: GraphNodeV1[], edges: GraphEdgeV1[]): GraphData {
  const nodeIds = new Set(nodes.map((n) => n.id));
  return {
    nodes: [...nodes],
    links: edges
      .filter((e) => nodeIds.has(e.source) && nodeIds.has(e.target))
      .map((e) => ({ source: e.source, target: e.target, type: e.type })),
  };
}

export default function SecondBrainGraphPage() {
  const { tenantId, spaceId } = useTenantContextStore();
  const [nodes, setNodes] = useState<GraphNodeV1[]>([]);
  const [edges, setEdges] = useState<GraphEdgeV1[]>([]);
  const [stats, setStats] = useState<{ node_count: number; edge_count: number } | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedNode, setSelectedNode] = useState<GraphNodeV1 | null>(null);
  const [filterEntity, setFilterEntity] = useState<string>("all");
  const [filterLifeArea, setFilterLifeArea] = useState<string>("");
  const [filterProject, setFilterProject] = useState<string>("");
  const [filterSource, setFilterSource] = useState<string>("");
  const [showFilters, setShowFilters] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiClient.getGraphV1({
        tenant_id: tenantId ?? DEFAULT_TENANT_ID,
        space_id: spaceId ?? "all",
        life_area: filterLifeArea || undefined,
        project_id: filterProject || undefined,
        source: filterSource || undefined,
        entity_types: filterEntity === "all" ? undefined : filterEntity,
        limit_nodes: 2000,
      });
      setNodes(res.nodes);
      setEdges(res.edges);
      setStats(res.stats ?? null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load graph");
    } finally {
      setLoading(false);
    }
  }, [tenantId, spaceId, filterEntity, filterLifeArea, filterProject, filterSource]);

  useEffect(() => {
    load();
  }, [load]);

  const graphData = buildGraphData(nodes, edges);

  if (loading && nodes.length === 0) {
    return <PageSkeleton title subtitle tableRows={5} />;
  }

  if (error) {
    return (
      <div className="space-y-6" suppressHydrationWarning>
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-textMain">Life Graph</h1>
          <p className="mt-1 text-sm text-textSoft">Knowledge graph of tasks, projects, commitments, events, and people.</p>
        </div>
        <ErrorState message={error} onRetry={load} />
      </div>
    );
  }

  return (
    <div className="space-y-4" suppressHydrationWarning>
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-textMain">Life Graph</h1>
          <p className="mt-1 text-sm text-textSoft">
            Relationships between tasks, projects, commitments, life areas, events, and people.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button size="sm" variant="outline" onClick={() => setShowFilters((s) => !s)}>
            <Filter className="h-4 w-4 mr-1" />
            Filters
          </Button>
          <Button size="sm" variant="outline" onClick={() => void load()}>
            <RefreshCw className="h-4 w-4 mr-1" />
            Refresh
          </Button>
        </div>
      </div>

      {showFilters && (
        <Card className="rounded-xl border border-[color:var(--color-border-subtle)] bg-surface1/90">
          <CardHeader>
            <CardTitle className="text-sm">Filter graph</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-wrap gap-4">
            <div>
              <label className="text-xs text-textSoft">Entity type</label>
              <select
                value={filterEntity}
                onChange={(e) => setFilterEntity(e.target.value)}
                className="ml-2 rounded border border-[color:var(--color-border-subtle)] bg-surface2 px-2 py-1 text-sm text-textMain"
              >
                <option value="all">All</option>
                <option value="task">Task</option>
                <option value="project">Project</option>
                <option value="commitment">Commitment</option>
                <option value="life_area">Life area</option>
                <option value="event">Event</option>
                <option value="person">Person</option>
                <option value="source">Source</option>
              </select>
            </div>
            <div>
              <label className="text-xs text-textSoft">Life area (title)</label>
              <input
                type="text"
                value={filterLifeArea}
                onChange={(e) => setFilterLifeArea(e.target.value)}
                placeholder="e.g. Work"
                className="ml-2 rounded border border-[color:var(--color-border-subtle)] bg-surface2 px-2 py-1 text-sm text-textMain w-32"
              />
            </div>
            <div>
              <label className="text-xs text-textSoft">Project ID</label>
              <input
                type="text"
                value={filterProject}
                onChange={(e) => setFilterProject(e.target.value)}
                placeholder="UUID"
                className="ml-2 rounded border border-[color:var(--color-border-subtle)] bg-surface2 px-2 py-1 text-sm text-textMain w-48"
              />
            </div>
            <div>
              <label className="text-xs text-textSoft">Source</label>
              <input
                type="text"
                value={filterSource}
                onChange={(e) => setFilterSource(e.target.value)}
                placeholder="e.g. notion, email"
                className="ml-2 rounded border border-[color:var(--color-border-subtle)] bg-surface2 px-2 py-1 text-sm text-textMain w-32"
              />
            </div>
          </CardContent>
        </Card>
      )}

      <Card className="rounded-2xl border border-[color:var(--color-border-subtle)] bg-surface1/90 overflow-hidden">
        <CardHeader className="pb-2">
          <div className="flex items-center justify-between">
            <CardTitle className="text-base text-textMain">
              {stats ? `${stats.node_count} nodes, ${stats.edge_count} edges` : "Graph"}
            </CardTitle>
            <span className="text-xs text-textSoft">Drag to pan · Scroll to zoom · Click node for details</span>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          <div className="h-[600px] w-full bg-surface2/30">
            <ForceGraph2D
              graphData={graphData}
              nodeId="id"
              nodeLabel={(n: any) => {
                const node = n as GraphNodeV1;
                const type = node.type ?? "";
                return `${node.label ?? ""}\n(${type})`;
              }}
              nodeColor={(n: any) => {
                const node = n as GraphNodeV1;
                const t = node.type ?? "event";
                return NODE_COLORS[t] ?? "#6b7280";
              }}
              nodeVal={(n: any) => {
                const node = n as GraphNodeV1;
                const t = node.type ?? "";
                if (t === "life_area" || t === "project") return 12;
                if (t === "task" || t === "commitment") return 8;
                return 5;
              }}
              linkColor={() => "var(--color-border-strong, #475569)"}
              linkWidth={1}
              linkDirectionalParticles={0}
              onNodeClick={(n: any) => setSelectedNode(n as GraphNodeV1)}
              linkCurvature={0.1}
            />
          </div>
        </CardContent>
      </Card>

      {selectedNode && (
        <Card className="rounded-xl border border-[color:var(--color-border-subtle)] bg-surface1">
          <CardHeader>
            <CardTitle className="text-sm flex items-center justify-between">
              <span>Node: {selectedNode.label}</span>
              <Button size="sm" variant="ghost" onClick={() => setSelectedNode(null)}>Close</Button>
            </CardTitle>
          </CardHeader>
          <CardContent className="text-sm space-y-2">
            <p><span className="text-textSoft">Type:</span> {selectedNode.type}</p>
            <p><span className="text-textSoft">ID:</span> <code className="text-xs bg-surface2 px-1 rounded">{selectedNode.id}</code></p>
            {selectedNode.meta && Object.keys(selectedNode.meta).length > 0 && (
              <pre className="text-xs text-textSoft bg-surface2 p-2 rounded overflow-auto max-h-40">
                {JSON.stringify(selectedNode.meta, null, 2)}
              </pre>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
