"use client";

import React, { useEffect, useState, useCallback, useMemo, Suspense } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { PageSkeleton } from "@/components/dashboard/PageSkeleton";
import { ErrorState } from "@/components/feedback/ErrorState";
import { apiClient, type AgentV1, type AgentLogV1, type AgentActionV1 } from "@/lib/apiClient";
import { DEFAULT_TENANT_ID, DEFAULT_USER_ID } from "@/lib/constants";
import { useTenantContextStore } from "@/lib/stores/tenantContextStore";
import { useAuthStore } from "@/lib/stores/authStore";
import { Play, RefreshCw, List, Zap, FileText } from "lucide-react";

function formatDate(s: string | null | undefined): string {
  if (!s) return "—";
  try {
    return new Date(s).toLocaleString(undefined, { dateStyle: "short", timeStyle: "short" });
  } catch {
    return String(s);
  }
}

function AgentsContent() {
  const { tenantId } = useTenantContextStore();
  const { user, loaded } = useAuthStore();
  const [agents, setAgents] = useState<AgentV1[]>([]);
  const [logs, setLogs] = useState<AgentLogV1[]>([]);
  const [actions, setActions] = useState<AgentActionV1[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [typeFilter, setTypeFilter] = useState<string>("");
  const [selectedAgent, setSelectedAgent] = useState<AgentV1 | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [runningId, setRunningId] = useState<string | null>(null);
  const [runResult, setRunResult] = useState<Record<string, unknown> | null>(null);
  const [activeTab, setActiveTab] = useState<"agents" | "logs" | "actions">("agents");

  const skipAuth = process.env.NEXT_PUBLIC_SKIP_AUTH === "1";
  const tenant_id = tenantId ?? DEFAULT_TENANT_ID;

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [agentsRes, logsRes, actionsRes] = await Promise.all([
        apiClient.listAgentsV1({ tenant_id }),
        apiClient.getAgentLogsV1({ tenant_id, limit: 100 }),
        apiClient.getAgentActionsV1({ tenant_id, limit: 100 }),
      ]);
      setAgents(Array.isArray(agentsRes) ? agentsRes : []);
      setLogs(Array.isArray(logsRes) ? logsRes : []);
      setActions(Array.isArray(actionsRes) ? actionsRes : []);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load");
    } finally {
      setLoading(false);
    }
  }, [tenant_id]);

  useEffect(() => {
    if (loaded && (user || skipAuth)) load();
  }, [load, loaded, user, skipAuth]);

  const handleRunAgent = useCallback(
    async (agent: AgentV1) => {
      setRunningId(agent.id);
      setRunResult(null);
      try {
        const res =         await apiClient.runAgentV1(agent.id, {
          tenant_id,
          space_id: "all",
          user_id: DEFAULT_USER_ID,
        });
        setRunResult({ ok: res.ok, agent_id: res.agent_id, result: res.result });
        await load();
      } catch (err) {
        setRunResult({ error: err instanceof Error ? err.message : "Run failed" });
      } finally {
        setRunningId(null);
      }
    },
    [tenant_id, load]
  );

  const filteredAgents = useMemo(
    () => (typeFilter ? agents.filter((a) => a.type === typeFilter) : agents),
    [agents, typeFilter]
  );
  const types = useMemo(
    () => Array.from(new Set(agents.map((a) => a.type).filter(Boolean))),
    [agents]
  );

  if (!loaded) {
    return <PageSkeleton title subtitle tableRows={8} />;
  }
  if (loaded && !user && !skipAuth) {
    return <PageSkeleton title subtitle tableRows={8} />;
  }

  if (loading && agents.length === 0) {
    return <PageSkeleton title subtitle tableRows={8} />;
  }

  return (
    <div className="space-y-6" suppressHydrationWarning>
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-textMain">Agents</h1>
        <p className="text-sm text-textSoft mt-1">
          Autonomous reasoning units: plan, insights, reminders, execution, overload, conflict. Run manually and view logs and actions.
        </p>
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <Select value={typeFilter || "all"} onValueChange={(v: string) => setTypeFilter(v === "all" ? "" : v)}>
          <SelectTrigger className="w-[160px] rounded-full border border-[color:var(--color-border-subtle)] bg-surface2 text-xs text-textMain">
            <SelectValue placeholder="Type" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All types</SelectItem>
            {types.map((t) => (
              <SelectItem key={t} value={t}>{t}</SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Button variant="outline" size="sm" onClick={() => void load()}>
          <RefreshCw className="h-4 w-4 mr-1" />
          Refresh
        </Button>
      </div>

      <div className="flex gap-2 border-b border-[color:var(--color-border-subtle)] pb-2">
        <button
          type="button"
          onClick={() => setActiveTab("agents")}
          className={`flex items-center gap-2 rounded-full px-4 py-2 text-sm font-medium ${activeTab === "agents" ? "bg-primary text-bg" : "bg-surface2 text-textMain hover:bg-surface3"}`}
        >
          <Zap className="h-4 w-4" />
          Agents
        </button>
        <button
          type="button"
          onClick={() => setActiveTab("logs")}
          className={`flex items-center gap-2 rounded-full px-4 py-2 text-sm font-medium ${activeTab === "logs" ? "bg-primary text-bg" : "bg-surface2 text-textMain hover:bg-surface3"}`}
        >
          <List className="h-4 w-4" />
          Logs
        </button>
        <button
          type="button"
          onClick={() => setActiveTab("actions")}
          className={`flex items-center gap-2 rounded-full px-4 py-2 text-sm font-medium ${activeTab === "actions" ? "bg-primary text-bg" : "bg-surface2 text-textMain hover:bg-surface3"}`}
        >
          <FileText className="h-4 w-4" />
          Actions
        </button>
      </div>

      {error && <ErrorState message={error} onRetry={load} />}

      {activeTab === "agents" && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {filteredAgents.map((agent) => (
            <Card
              key={agent.id}
              className="cursor-pointer transition-transform hover:scale-[1.01]"
              onClick={() => {
                setSelectedAgent(agent);
                setRunResult(null);
                setDrawerOpen(true);
              }}
            >
              <CardHeader className="pb-3">
                <CardTitle className="text-sm flex items-center justify-between gap-2">
                  <span className="truncate">{agent.name}</span>
                  <span className="rounded-full bg-surface2 px-2 py-0.5 text-[10px] uppercase text-textSoft">{agent.type}</span>
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3 text-xs text-textSoft">
                {agent.description && <p className="line-clamp-3">{agent.description}</p>}
                <p className="text-[11px]">Last run: {formatDate(agent.last_run)}</p>
                <div className="flex justify-end pt-1">
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={runningId === agent.id}
                    onClick={(e: React.MouseEvent) => {
                      e.stopPropagation();
                      handleRunAgent(agent);
                    }}
                  >
                    <Play className="h-3 w-3 mr-1" />
                    {runningId === agent.id ? "Running…" : "Run now"}
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {activeTab === "logs" && (
        <Card className="rounded-2xl border border-[color:var(--color-border-subtle)] bg-surface1/90">
          <CardHeader>
            <CardTitle className="text-base">Agent run logs</CardTitle>
            <p className="text-xs text-textSoft">Timestamp, duration, result count, errors.</p>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-[color:var(--color-border-subtle)] text-left text-textSoft">
                    <th className="pb-2 pr-4">Agent</th>
                    <th className="pb-2 pr-4">Run at</th>
                    <th className="pb-2 pr-4">Duration (ms)</th>
                    <th className="pb-2 pr-4">Results</th>
                    <th className="pb-2">Errors</th>
                  </tr>
                </thead>
                <tbody>
                  {logs.map((log, i) => (
                    <tr key={i} className="border-b border-[color:var(--color-border-subtle)]/50">
                      <td className="py-2 pr-4 font-medium text-textMain">{log.agent_name}</td>
                      <td className="py-2 pr-4 text-textSoft">{formatDate(log.run_at)}</td>
                      <td className="py-2 pr-4 text-textSoft">{log.duration_ms?.toFixed(0) ?? "—"}</td>
                      <td className="py-2 pr-4 text-textSoft">{log.result_count ?? 0}</td>
                      <td className="py-2 text-textSoft">{log.errors?.length ? log.errors.join("; ") : "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {logs.length === 0 && <p className="py-8 text-center text-textSoft">No logs yet. Run an agent to see logs.</p>}
          </CardContent>
        </Card>
      )}

      {activeTab === "actions" && (
        <Card className="rounded-2xl border border-[color:var(--color-border-subtle)] bg-surface1/90">
          <CardHeader>
            <CardTitle className="text-base">Agent actions</CardTitle>
            <p className="text-xs text-textSoft">Pending, executed, failed.</p>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-[color:var(--color-border-subtle)] text-left text-textSoft">
                    <th className="pb-2 pr-4">Agent</th>
                    <th className="pb-2 pr-4">Type</th>
                    <th className="pb-2 pr-4">Status</th>
                    <th className="pb-2 pr-4">Created</th>
                    <th className="pb-2">Error</th>
                  </tr>
                </thead>
                <tbody>
                  {actions.map((a) => (
                    <tr key={a.id} className="border-b border-[color:var(--color-border-subtle)]/50">
                      <td className="py-2 pr-4 font-medium text-textMain">{a.agent}</td>
                      <td className="py-2 pr-4 text-textSoft">{a.type}</td>
                      <td className="py-2 pr-4 text-textSoft">{a.status}</td>
                      <td className="py-2 pr-4 text-textSoft">{formatDate(a.created_at)}</td>
                      <td className="py-2 text-textSoft">{a.error ?? "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {actions.length === 0 && <p className="py-8 text-center text-textSoft">No actions yet.</p>}
          </CardContent>
        </Card>
      )}

      <Sheet open={drawerOpen} onOpenChange={setDrawerOpen}>
        <SheetContent side="right" className="w-full max-w-md bg-surface1 border-l border-[color:var(--color-border-subtle)]">
          <SheetHeader>
            <SheetTitle className="text-sm font-semibold text-textMain">Agent details</SheetTitle>
          </SheetHeader>
          {selectedAgent && (
            <div className="mt-4 space-y-4 text-sm">
              <div>
                <p className="text-xs font-medium text-textSoft">Name</p>
                <p className="text-textMain">{selectedAgent.name}</p>
              </div>
              <div>
                <p className="text-xs font-medium text-textSoft">Type</p>
                <p className="text-textMain">{selectedAgent.type}</p>
              </div>
              <div>
                <p className="text-xs font-medium text-textSoft">Triggers</p>
                <p className="text-textMain">{selectedAgent.triggers?.join(", ") || "—"}</p>
              </div>
              <div>
                <p className="text-xs font-medium text-textSoft">Last run</p>
                <p className="text-textMain">{formatDate(selectedAgent.last_run)}</p>
              </div>
              <Button className="w-full" size="sm" disabled={runningId === selectedAgent.id} onClick={() => handleRunAgent(selectedAgent)}>
                <Play className="h-3 w-3 mr-1" />
                {runningId === selectedAgent.id ? "Running…" : "Run now"}
              </Button>
              {runResult && (
                <div className="mt-4 rounded-xl border border-[color:var(--color-border-subtle)] bg-surface2/70 p-2 text-xs overflow-auto max-h-[300px]">
                  <pre className="whitespace-pre-wrap text-textMain">{JSON.stringify(runResult, null, 2)}</pre>
                </div>
              )}
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
