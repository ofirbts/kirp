"use client";

import React, { useEffect, useState, useCallback, Suspense } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { DataTable } from "@/components/dashboard/DataTable";
import { PageSkeleton } from "@/components/dashboard/PageSkeleton";
import { ErrorState } from "@/components/feedback/ErrorState";
import { apiClient } from "@/lib/apiClient";
import { useTenantContextStore } from "@/lib/stores/tenantContextStore";
import type { Agent } from "@/lib/types";

function AgentsContent() {
  const { tenantId, spaceId } = useTenantContextStore();
  const [agents, setAgents] = useState<Agent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [typeFilter, setTypeFilter] = useState<string>("");
  const [selectedAgent, setSelectedAgent] = useState<Agent | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiClient.listAgents({
        tenantId: tenantId ?? "default",
        spaceId: spaceId ?? "all",
        status: statusFilter || undefined,
        type: typeFilter || undefined,
      });
      setAgents(res.data ?? []);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load agents");
    } finally {
      setLoading(false);
    }
  }, [tenantId, spaceId, statusFilter, typeFilter]);

  useEffect(() => {
    load();
  }, [load]);

  if (loading && agents.length === 0) {
    return <PageSkeleton title subtitle cards={0} tableRows={8} />;
  }

  return (
    <div className="space-y-6" suppressHydrationWarning>
      <div suppressHydrationWarning>
        <h1 className="text-2xl font-bold tracking-tight">Agents</h1>
        <p className="text-muted-foreground text-sm mt-1">
          Manage and inspect intelligence agents.
        </p>
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <Select value={statusFilter || "all"} onValueChange={(v) => setStatusFilter(v === "all" ? "" : v)}>
          <SelectTrigger className="w-[140px] border-neutral-700 bg-neutral-900">
            <SelectValue placeholder="Status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All statuses</SelectItem>
            <SelectItem value="active">Active</SelectItem>
            <SelectItem value="paused">Paused</SelectItem>
            <SelectItem value="error">Error</SelectItem>
          </SelectContent>
        </Select>
        <Select value={typeFilter || "all"} onValueChange={(v) => setTypeFilter(v === "all" ? "" : v)}>
          <SelectTrigger className="w-[160px] border-neutral-700 bg-neutral-900">
            <SelectValue placeholder="Type" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All types</SelectItem>
            <SelectItem value="retrieval">Retrieval</SelectItem>
            <SelectItem value="planner">Planner</SelectItem>
            <SelectItem value="executor">Executor</SelectItem>
            <SelectItem value="governance">Governance</SelectItem>
            <SelectItem value="other">Other</SelectItem>
          </SelectContent>
        </Select>
        <Button variant="outline" size="sm" onClick={load}>
          Refresh
        </Button>
      </div>

      {error && (
        <ErrorState message={error} onRetry={load} />
      )}

      <DataTable<Agent>
        title="Agents"
        data={agents}
        keyExtractor={(r) => r.id}
        loading={loading}
        error={error}
        onRetry={load}
        columns={[
          { key: "name", header: "Name", render: (r) => r.name },
          { key: "type", header: "Type", render: (r) => r.type },
          { key: "status", header: "Status", render: (r) => r.status },
          { key: "tenantId", header: "Tenant", render: (r) => r.tenantId },
        ]}
        emptyMessage="No agents match the filters."
        pageSize={10}
        onRowClick={(row) => {
          setSelectedAgent(row);
          setDrawerOpen(true);
        }}
      />

      <Sheet open={drawerOpen} onOpenChange={setDrawerOpen}>
        <SheetContent side="right" className="w-full max-w-md border-neutral-800 bg-neutral-950">
          <SheetHeader>
            <SheetTitle className="text-sm font-semibold text-neutral-100">
              Agent details
            </SheetTitle>
          </SheetHeader>
          {selectedAgent && (
            <div className="mt-4 space-y-4 text-sm">
              <div>
                <p className="text-xs font-medium text-neutral-500">ID</p>
                <p className="font-mono text-xs text-neutral-300">{selectedAgent.id}</p>
              </div>
              <div>
                <p className="text-xs font-medium text-neutral-500">Name</p>
                <p className="text-neutral-200">{selectedAgent.name}</p>
              </div>
              <div>
                <p className="text-xs font-medium text-neutral-500">Type / Status</p>
                <p className="text-neutral-200">{selectedAgent.type} · {selectedAgent.status}</p>
              </div>
              {selectedAgent.description && (
                <div>
                  <p className="text-xs font-medium text-neutral-500">Description</p>
                  <p className="text-neutral-400">{selectedAgent.description}</p>
                </div>
              )}
              <div>
                <p className="text-xs font-medium text-neutral-500">Metrics (local)</p>
                <p className="text-xs text-neutral-500">
                  No backend metrics endpoint; display derived from agent list only.
                </p>
              </div>
            </div>
          )}
        </SheetContent>
      </Sheet>
    </div>
  );
}

export default function AgentsPage() {
  return (
    <Suspense fallback={<PageSkeleton title subtitle tableRows={8} />}>
      <AgentsContent />
    </Suspense>
  );
}
