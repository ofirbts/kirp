"use client";

import React, { useCallback, useEffect, useState, Suspense } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { PageSkeleton } from "@/components/dashboard/PageSkeleton";
import { ErrorState } from "@/components/feedback/ErrorState";
import { apiClient, type SchemaNodeV1 } from "@/lib/apiClient";
import { DEFAULT_TENANT_ID } from "@/lib/constants";
import { useTenantContextStore } from "@/lib/stores/tenantContextStore";
import { LayoutGrid, Briefcase, Heart, Users, BookOpen } from "lucide-react";

const LIFE_AREAS = [
  { name: "Work", icon: Briefcase, color: "text-amber-500" },
  { name: "Family", icon: Users, color: "text-emerald-500" },
  { name: "Health", icon: Heart, color: "text-rose-500" },
  { name: "Learning", icon: BookOpen, color: "text-violet-500" },
];

function formatDate(s: string | null | undefined): string {
  if (!s) return "";
  try {
    return new Date(s).toLocaleDateString(undefined, { dateStyle: "short", timeZone: "UTC" });
  } catch {
    return String(s);
  }
}

function LifeAreasContent() {
  const { tenantId, spaceId } = useTenantContextStore();
  const [nodes, setNodes] = useState<SchemaNodeV1[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [lifeRes, commitmentRes, taskRes] = await Promise.all([
        apiClient.listNodesV1({
          tenant_id: DEFAULT_TENANT_ID,
          space_id: spaceId ?? "all",
          entity: "life_area",
          limit: 50,
        }),
        apiClient.listNodesV1({
          tenant_id: DEFAULT_TENANT_ID,
          space_id: spaceId ?? "all",
          entity: "commitment",
          limit: 200,
        }),
        apiClient.listNodesV1({
          tenant_id: DEFAULT_TENANT_ID,
          space_id: spaceId ?? "all",
          entity: "task",
          limit: 200,
        }),
      ]);
      setNodes([
        ...(lifeRes.data ?? []),
        ...(commitmentRes.data ?? []),
        ...(taskRes.data ?? []),
      ]);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load life areas");
    } finally {
      setLoading(false);
    }
  }, [tenantId, spaceId]);

  useEffect(() => {
    load();
  }, [load]);

  if (loading) {
    return <PageSkeleton title subtitle cards={4} tableRows={6} />;
  }

  if (error) {
    return (
      <div className="space-y-6" suppressHydrationWarning>
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-textMain">Life Areas</h1>
          <p className="mt-1 text-sm text-textSoft">Work, Family, Health, Learning.</p>
        </div>
        <ErrorState message={error} onRetry={load} />
      </div>
    );
  }

  const lifeAreaNodes = nodes.filter((n) => n.entity === "life_area");
  const commitments = nodes.filter((n) => n.entity === "commitment");
  const tasks = nodes.filter((n) => n.entity === "task");

  const byLifeArea = LIFE_AREAS.map((area) => {
    const areaNode = lifeAreaNodes.find((n) => n.title === area.name);
    const areaCommitments = commitments.filter(
      (c) => c.parent_id === areaNode?.id || (c.metadata as Record<string, string> | undefined)?.life_area === area.name
    );
    const areaTasks = tasks.filter(
      (t) => (t.metadata as Record<string, string> | undefined)?.life_area === area.name
    );
    return {
      ...area,
      commitments: areaCommitments,
      tasks: areaTasks,
      node: areaNode,
    };
  });

  return (
    <div className="space-y-6" suppressHydrationWarning>
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between" suppressHydrationWarning>
        <div suppressHydrationWarning>
          <h1 className="text-2xl font-bold tracking-tight text-textMain flex items-center gap-2">
            <LayoutGrid className="h-7 w-7 text-primary" />
            Life Areas
          </h1>
          <p className="mt-1 text-sm text-textSoft">
            Work, Family, Health, Learning — commitments and tasks by area.
          </p>
        </div>
        <button
          type="button"
          onClick={() => load()}
          className="rounded-full border border-[color:var(--color-border-subtle)] bg-surface2 px-3 py-2 text-xs text-textMain hover:bg-surface3"
        >
          Refresh
        </button>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {byLifeArea.map(({ name, icon: Icon, color, commitments: comms, tasks: tsks }) => (
          <Card
            key={name}
            className="rounded-2xl border border-[color:var(--color-border-subtle)] bg-surface1/90 shadow-soft"
          >
            <CardHeader className="pb-2">
              <CardTitle className="flex items-center gap-2 text-base text-textMain">
                <Icon className={`h-5 w-5 ${color}`} />
                {name}
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <p className="text-xs text-textSoft">
                {comms.length} commitment{comms.length !== 1 ? "s" : ""}, {tsks.length} task{tsks.length !== 1 ? "s" : ""}
              </p>
              <ul className="space-y-1.5 max-h-40 overflow-auto text-sm">
                {comms.slice(0, 5).map((c) => (
                  <li key={c.id} className="text-textMain truncate" title={c.title}>
                    {c.title}
                  </li>
                ))}
                {tsks.slice(0, 3).map((t) => (
                  <li key={t.id} className="text-textSoft truncate pl-2 border-l border-[color:var(--color-border-subtle)]" title={t.title}>
                    {t.title}
                    {t.due_date && (
                      <span className="text-[10px] ml-1">{formatDate(t.due_date)}</span>
                    )}
                  </li>
                ))}
                {comms.length === 0 && tsks.length === 0 && (
                  <li className="text-textSoft">Nothing yet</li>
                )}
              </ul>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}

export default function LifeAreasPage() {
  return (
    <Suspense fallback={<PageSkeleton title subtitle cards={4} />}>
      <LifeAreasContent />
    </Suspense>
  );
}
