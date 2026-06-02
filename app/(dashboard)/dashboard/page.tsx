"use client";

import React, { useEffect, useRef, useState, Suspense } from "react";
import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { PageSkeleton } from "@/components/dashboard/PageSkeleton";
import { DataTable } from "@/components/dashboard/DataTable";
import { ErrorState } from "@/components/feedback/ErrorState";
import { StatsCard } from "@/components/ui/stats-card";
import { RadialChart } from "@/components/charts/RadialChart";
import { EventRateChart } from "@/components/data/EventRateChart";
import {
  apiClient,
  getRecentAuthFailureCount,
  getRuntimeVersionHint,
  type AskResponse,
  type InsightV1,
  type TenantUsageDetailsV1,
} from "@/lib/apiClient";
import type { Event, Agent } from "@/lib/types";
import { Activity, Database, HeartPulse, ListChecks, Zap, Cpu, Lightbulb } from "lucide-react";
import { DEFAULT_TENANT_ID } from "@/lib/constants";
import { useTenantContextStore } from "@/lib/stores/tenantContextStore";
import { useAuthStore } from "@/lib/stores/authStore";
import type { TaskV1 } from "@/lib/apiClient";

function formatUtcDate(iso: string | null | undefined): string {
  if (!iso) return "";
  try {
    return new Date(iso).toISOString().slice(0, 10);
  } catch {
    return String(iso);
  }
}

function formatUtcDateTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toISOString().replace("T", " ").slice(0, 19) + " UTC";
  } catch {
    return String(iso);
  }
}

// Legacy dashboard (kept for reference; not rendered anymore)
function DashboardContent() {
  const { spaceId } = useTenantContextStore();
  const { user } = useAuthStore();
  const tenantId = user?.tenant_id ?? DEFAULT_TENANT_ID;
  const userId = user?.id ?? null;
  const [stats, setStats] = useState<Record<string, unknown> | null>(null);
  const [events, setEvents] = useState<Event[]>([]);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [insights, setInsights] = useState<InsightV1[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [ingestSuccess, setIngestSuccess] = useState<string | null>(null);
  const [ingestLoading, setIngestLoading] = useState(false);
  const [quickContent, setQuickContent] = useState("");
  const [askQuery, setAskQuery] = useState("");
  const [askAnswer, setAskAnswer] = useState<string | null>(null);
  const [askSources, setAskSources] = useState<unknown[] | null>(null);
  const [askLoading, setAskLoading] = useState(false);

  const load = React.useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [statsRes, eventsRes, agentsRes, insightsRes] = await Promise.all([
        apiClient.getStats().catch(() => ({})),
        apiClient.listEvents({}).then((r) => r.data ?? []),
        apiClient.listAgents({}).then((r) => r.data ?? []),
        apiClient.getInsightsV1({
          space_id: spaceId ?? "all",
          limit: 30,
        }).catch(() => []),
      ]);
      setStats(statsRes as Record<string, unknown>);
      setEvents(eventsRes);
      setAgents(agentsRes);
      setInsights(Array.isArray(insightsRes) ? insightsRes : []);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load dashboard");
    } finally {
      setLoading(false);
    }
  }, [spaceId]);

  useEffect(() => {
    load();
  }, [load]);

  async function handleQuickIngest() {
    if (!quickContent.trim() || !userId) return;
    setIngestLoading(true);
    setIngestSuccess(null);
    try {
      await apiClient.ingestV1({
        tenant_id: tenantId,
        space_id: spaceId ?? "all",
        user_id: userId,
        content: quickContent.trim(),
        source: "dashboard",
      });
      setQuickContent("");
      setIngestSuccess("Added. Refreshing…");
      await load();
      setIngestSuccess("Knowledge added.");
      setTimeout(() => setIngestSuccess(null), 3000);
    } catch (e) {
      setIngestSuccess(null);
      setError(e instanceof Error ? e.message : "Ingest failed");
    } finally {
      setIngestLoading(false);
    }
  }

  async function handleAsk() {
    if (!askQuery.trim()) return;
    setAskLoading(true);
    setAskAnswer(null);
    setAskSources(null);
    try {
      const res = await apiClient.askV1({ query: askQuery.trim() });
      setAskAnswer(res.answer);
      setAskSources(res.sources);
    } catch (e) {
      setAskAnswer(
        e instanceof Error ? e.message : "Ask failed. Check that the API is reachable.",
      );
      setAskSources(null);
    } finally {
      setAskLoading(false);
    }
  }

  if (loading) {
    return (
      <PageSkeleton
        title
        subtitle
        cards={4}
        tableRows={5}
      />
    );
  }

  if (error) {
    return (
      <div className="space-y-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Dashboard</h1>
          <p className="text-muted-foreground text-sm mt-1">
            System health, KPIs, and overview.
          </p>
        </div>
        <ErrorState message={error} onRetry={load} />
      </div>
    );
  }

  const knowledgeItems = typeof stats?.knowledge_items === "number" ? stats.knowledge_items : 0;
  const activeJobs = typeof stats?.active_jobs === "number" ? stats.active_jobs : 0;
  const newInsights = insights.length > 0 ? insights.length : (typeof stats?.new_insights === "number" ? stats.new_insights : 0);
  const agentCount = typeof stats?.agents === "number" ? stats.agents : agents.length;

  const radialData = [
    { name: "Knowledge", value: knowledgeItems },
    { name: "Jobs", value: activeJobs },
    { name: "Insights", value: newInsights },
    { name: "Agents", value: agentCount },
  ].filter((d) => d.value > 0).length
    ? [
        { name: "Knowledge", value: Math.max(1, knowledgeItems) },
        { name: "Jobs", value: Math.max(1, activeJobs) },
        { name: "Insights", value: Math.max(1, newInsights) },
        { name: "Agents", value: Math.max(1, agentCount) },
      ]
    : [
        { name: "Knowledge", value: 1 },
        { name: "Jobs", value: 1 },
        { name: "Insights", value: 1 },
        { name: "Agents", value: 1 },
      ];

  return (
    <div className="space-y-6" suppressHydrationWarning>
      <div suppressHydrationWarning>
        <h1 className="text-2xl font-bold tracking-tight">Dashboard</h1>
        <p className="text-muted-foreground text-sm mt-1">
          System health, KPIs, and overview.
        </p>
      </div>

      {/* Ask / Search / Insights bar */}
      <div className="rounded-lg border border-neutral-800 bg-neutral-900/80 p-4 space-y-3">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-sm font-medium text-neutral-200">Ask / Search / Insights</p>
            <p className="text-xs text-neutral-400">
              Ask anything about your life, work, habits or plans – scoped to your KIRP data.
            </p>
          </div>
        </div>
        <div className="flex flex-wrap items-end gap-2">
          <input
            className="min-w-[260px] flex-1 rounded border border-neutral-700 bg-neutral-900 px-3 py-2 text-sm text-neutral-100 placeholder:text-neutral-500"
            placeholder="Ask anything about your life, work, habits or plans…"
            value={askQuery}
            onChange={(e) => setAskQuery(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                void handleAsk();
              }
            }}
          />
          <button
            type="button"
            onClick={() => void handleAsk()}
            disabled={askLoading}
            className="inline-flex items-center rounded-md border border-cyan-500/70 bg-cyan-600/90 px-3 py-2 text-sm font-medium text-neutral-50 hover:bg-cyan-500 disabled:opacity-60"
          >
            {askLoading ? "Thinking…" : "Ask"}
          </button>
        </div>
        {askAnswer && (
          <div className="mt-3 rounded-md border border-neutral-700 bg-neutral-900/80 p-3 text-sm text-neutral-100">
            <p className="whitespace-pre-wrap">{askAnswer}</p>
            {askSources && askSources.length > 0 && (
              <details className="mt-2 text-xs text-neutral-400">
                <summary className="cursor-pointer text-neutral-300">Sources</summary>
                <pre className="mt-1 max-h-64 overflow-auto whitespace-pre-wrap rounded bg-neutral-950/70 p-2 text-[11px]">
                  {JSON.stringify(askSources, null, 2)}
                </pre>
              </details>
            )}
          </div>
        )}
      </div>

      <div className="rounded-lg border border-neutral-800 bg-neutral-900/70 p-4">
        <h3 className="text-sm font-medium text-neutral-200 mb-2">Quick add knowledge (event-sourced)</h3>
        <div className="flex flex-wrap items-end gap-2">
          <input
            className="min-w-[240px] rounded border border-neutral-700 bg-neutral-900 px-3 py-2 text-sm text-neutral-100 placeholder:text-neutral-500"
            placeholder="Add a note, task, or insight…"
            value={quickContent}
            onChange={(e) => setQuickContent(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && (e.preventDefault(), handleQuickIngest())}
          />
          <button
            type="button"
            disabled={ingestLoading || !quickContent.trim() || !userId}
            onClick={handleQuickIngest}
            className="rounded bg-cyan-600 px-3 py-2 text-sm font-medium text-white hover:bg-cyan-500 disabled:opacity-50"
          >
            {ingestLoading ? "Adding…" : "Add"}
          </button>
        </div>
        {ingestSuccess && <p className="mt-2 text-xs text-green-400">{ingestSuccess}</p>}
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <StatsCard
          title="Knowledge items"
          value={knowledgeItems}
          icon={Database}
        />
        <StatsCard
          title="Active jobs"
          value={activeJobs}
          icon={Zap}
        />
        <StatsCard
          title="New insights"
          value={newInsights}
          icon={Activity}
        />
        <StatsCard
          title="Agents"
          value={agentCount}
          icon={Cpu}
        />
      </div>

      {/* Insights from Events → Tasks → Projects → Commitments → Schedules → Life Areas */}
      {insights.length > 0 && (
        <Card className="border-neutral-800 bg-neutral-900/70">
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <Lightbulb className="h-4 w-4 text-amber-400" />
              Insights — workload, patterns, commitments, recommendations
            </CardTitle>
            <p className="text-xs text-neutral-400">
              Real insights from your data, not generic text.
            </p>
          </CardHeader>
          <CardContent>
            <ul className="space-y-3">
              {insights.slice(0, 12).map((i) => (
                <li
                  key={i.id}
                  className="rounded-lg border border-neutral-700/80 bg-neutral-900/50 p-3"
                >
                  <span className="text-xs font-medium text-cyan-400/90">{i.category}</span>
                  <h4 className="mt-0.5 font-medium text-neutral-100">{i.title}</h4>
                  <p className="mt-1 text-sm text-neutral-300 whitespace-pre-wrap">{i.body}</p>
                  {i.confidence > 0 && i.confidence < 1 && (
                    <p className="mt-1 text-xs text-neutral-500">Confidence: {Math.round(i.confidence * 100)}%</p>
                  )}
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        <Card className="border-neutral-800 bg-neutral-900/70">
          <CardHeader>
            <CardTitle className="text-base">KPIs by category</CardTitle>
          </CardHeader>
          <CardContent>
            <RadialChart data={radialData} height={260} />
          </CardContent>
        </Card>
        <EventRateChart events={events} />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <DataTable<Event>
          title="Recent events"
          data={events}
          keyExtractor={(r: Event) => r.id}
          columns={[
            { key: "topic", header: "Topic", render: (r: Event) => r.topic || "—" },
            { key: "severity", header: "Severity", render: (r: Event) => r.severity },
            { key: "timestamp", header: "Time", render: (r: Event) => r.timestamp?.slice(0, 19) ?? "—" },
          ]}
          emptyMessage="No recent events."
          pageSize={10}
        />
        <DataTable<Agent>
          title="Active agents"
          data={agents}
          keyExtractor={(r: Agent) => r.id}
          columns={[
            { key: "name", header: "Name", render: (r: Agent) => r.name },
            { key: "type", header: "Type", render: (r: Agent) => r.type },
            { key: "status", header: "Status", render: (r: Agent) => r.status },
          ]}
          emptyMessage="No agents."
          pageSize={10}
        />
      </div>
    </div>
  );
}

function RealDashboardContent() {
  const { spaceId } = useTenantContextStore();
  const { user, loaded } = useAuthStore();
  const tenantId = user?.tenant_id ?? DEFAULT_TENANT_ID;
  const userId = user?.id ?? null;
  const [tasks, setTasks] = useState<TaskV1[]>([]);
  const [events, setEvents] = useState<Event[]>([]);
  const [health, setHealth] = useState<Record<string, unknown> | null>(null);
  const [insight, setInsight] = useState<AskResponse | null>(null);
  const [usage, setUsage] = useState<TenantUsageDetailsV1 | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [quickContent, setQuickContent] = useState("");
  const [ingestLoading, setIngestLoading] = useState(false);
  const [sampleIngestLoading, setSampleIngestLoading] = useState(false);
  const [ingestSuccess, setIngestSuccess] = useState<string | null>(null);
  const [ingestError, setIngestError] = useState<string | null>(null);
  const [ingestKindHint, setIngestKindHint] = useState<"task" | "info">("info");
  const [verifyState, setVerifyState] = useState<
    "processing" | "success" | "failure" | "network_issue" | null
  >(null);
  const [verifyProof, setVerifyProof] = useState<string | null>(null);
  const [runtimeVersionSha, setRuntimeVersionSha] = useState<string>("unknown");
  const [healthVersionSha, setHealthVersionSha] = useState<string>("unknown");
  const [apiHeaderVersionSha, setApiHeaderVersionSha] = useState<string>("unknown");
  const [runtimeBuildTime, setRuntimeBuildTime] = useState<string>("unknown");
  const [runtimeEnvironment, setRuntimeEnvironment] = useState<string>("unknown");
  const [authFailureSpike, setAuthFailureSpike] = useState(false);
  const [trustScore, setTrustScore] = useState<number>(100);
  const [trustReasons, setTrustReasons] = useState<string[]>([]);
  const [activeAutoRules, setActiveAutoRules] = useState<string[]>([]);
  const [currentBlockers, setCurrentBlockers] = useState<string[]>([]);
  const [unknownStates, setUnknownStates] = useState<string[]>([]);
  const [mounted, setMounted] = useState(false);
  const [hasHistory, setHasHistory] = useState(false);
  const mountedRef = useRef(true);

  const skipAuth = process.env.NEXT_PUBLIC_SKIP_AUTH === "1";

  useEffect(() => {
    setMounted(true);
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
    };
  }, []);

  const load = React.useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [tasksRes, eventsRes, healthRes, usageRes, runtimeHealth, historyRes] = await Promise.all([
        apiClient
          .listTasksV1({
            tenant_id: tenantId,
            space_id: spaceId ?? "all",
            status: undefined,
            limit: 50,
          })
          .catch(() => ({ data: [] })),
        apiClient
          .listEvents({
            tenantId: tenantId,
            spaceId: spaceId ?? "all",
          })
          .then((r) => r.data ?? [])
          .catch(() => []),
        apiClient.getObservabilityHealth().catch(() => null),
        apiClient.getTenantUsageDetailsV1(tenantId).catch(() => null),
        apiClient.getRuntimeHealthV1().catch(() => null),
        apiClient
          .listHistoryV1({
            tenant_id: tenantId,
            user_id: userId ?? undefined,
            limit: 1,
          })
          .catch(() => []),
      ]);
      if (!mountedRef.current) return;
      setTasks((tasksRes as { data?: TaskV1[] }).data ?? []);
      setEvents(eventsRes as Event[]);
      setHealth(healthRes as Record<string, unknown> | null);
      setUsage(usageRes as TenantUsageDetailsV1 | null);
      setHasHistory(Array.isArray(historyRes) && historyRes.length > 0);
      const fromHealth = runtimeHealth?.version?.sha?.trim();
      const fromHeader = getRuntimeVersionHint();
      const fromBuild = process.env.NEXT_PUBLIC_APP_GIT_SHA?.trim() || null;
      setHealthVersionSha(fromHealth || "unknown");
      setApiHeaderVersionSha(fromHeader || "unknown");
      setRuntimeBuildTime(runtimeHealth?.version?.build_time?.trim() || "unknown");
      setRuntimeEnvironment(runtimeHealth?.version?.environment?.trim() || "unknown");
      const resolved =
        (fromHealth && fromHealth !== "unknown" ? fromHealth : null) ||
        (fromHeader && fromHeader !== "unknown" ? fromHeader : null) ||
        (fromBuild && fromBuild !== "unknown" ? fromBuild : null) ||
        "unknown";
      setRuntimeVersionSha(resolved);
      setAuthFailureSpike(getRecentAuthFailureCount() >= 5);
      const reasons: string[] = [];
      let score = 100;
      const hasUnknownVersion =
        resolved === "unknown" ||
        (runtimeHealth?.version?.sha?.trim() || "unknown") === "unknown" ||
        (fromHeader || "unknown") === "unknown";
      const hasMismatch = [fromHealth, fromHeader, fromBuild]
        .filter((v): v is string => Boolean(v && v !== "unknown"))
        .filter((v, i, arr) => arr.indexOf(v) !== i).length > 0;
      if (hasUnknownVersion) {
        score -= 40;
        reasons.push("runtime-version-unknown");
      }
      if (hasMismatch) {
        score -= 20;
        reasons.push("runtime-version-mismatch");
      }
      if (getRecentAuthFailureCount() >= 5) {
        score -= 20;
        reasons.push("auth-failure-spike");
      }
      const autoRules: string[] = [];
      if (getRecentAuthFailureCount() >= 5) {
        autoRules.push("auto-auth_failure-threshold");
      }
      const unknowns: string[] = [];
      if (hasUnknownVersion) unknowns.push("runtime-version-unknown");
      const blockers: string[] = [];
      if (score < 80) blockers.push("trust-score-below-threshold");
      if (unknowns.length > 0) blockers.push("unknown-state-detected");
      setActiveAutoRules(autoRules);
      setUnknownStates(unknowns);
      setCurrentBlockers(blockers);
      setTrustScore(Math.max(0, Math.min(100, score)));
      setTrustReasons(reasons);
    } catch (e) {
      if (!mountedRef.current) return;
      setError(e instanceof Error ? e.message : "Failed to load dashboard");
    } finally {
      if (!mountedRef.current) return;
      setLoading(false);
    }
  }, [spaceId, tenantId, userId]);

  useEffect(() => {
    if (loaded && (user || skipAuth)) load();
  }, [load, loaded, user, skipAuth]);

  useEffect(() => {
    if (!loaded || (!user && !skipAuth)) return;
    let cancelled = false;
    void apiClient
      .askV1({ query: "What should I focus on today?" })
      .then((res) => {
        if (!cancelled) setInsight(res as AskResponse);
      })
      .catch(() => {
        if (!cancelled) setInsight(null);
      });
    return () => {
      cancelled = true;
    };
  }, [loaded, user, skipAuth, tenantId, spaceId]);

  useEffect(() => {
    const text = quickContent.trim();
    if (!text) {
      setIngestKindHint("info");
      return;
    }
    const lower = text.toLowerCase();
    const isTaskLike =
      lower.startsWith("משימה:") ||
      lower.startsWith("task:") ||
      lower.startsWith("todo:") ||
      /(?:מחר|שבוע הבא|יום\s+\S+|דדליין|צריך|חייב|להגיש|לבצע|לסיים)/.test(text) ||
      /\b(todo|task|due|deadline|need to|must)\b/.test(lower);
    setIngestKindHint(isTaskLike ? "task" : "info");
  }, [quickContent]);

  async function waitForRunCompletion(
    runId: string,
    timeoutMs = 10000,
  ): Promise<
    | { kind: "ok"; vis: Awaited<ReturnType<typeof apiClient.getRunVisibilityV1>> }
    | { kind: "network_error"; vis: null }
    | { kind: "timeout"; vis: null }
  > {
    const poll = apiClient.getRunVisibilityV1(runId)
      .then((vis) => ({ kind: "ok" as const, vis }))
      .catch(() => ({ kind: "network_error" as const, vis: null }));
    const timer = new Promise<{ kind: "timeout"; vis: null }>((resolve) =>
      setTimeout(() => resolve({ kind: "timeout", vis: null }), timeoutMs),
    );
    return Promise.race([poll, timer]);
  }

  if (!mounted || !loaded) {
    return <PageSkeleton title subtitle cards={4} tableRows={5} />;
  }
  if (loaded && !user && !skipAuth) {
    return <PageSkeleton title subtitle cards={4} tableRows={5} />;
  }

  async function handleQuickIngest() {
    if (!quickContent.trim() || !userId) return;
    setIngestLoading(true);
    setIngestSuccess(null);
    setIngestError(null);
    setVerifyState(null);
    setVerifyProof(null);
    try {
      const payload = quickContent.trim();
      const ingestRes = (await apiClient.ingestV1({
        tenant_id: tenantId,
        space_id: spaceId ?? "all",
        user_id: userId,
        content: payload,
        source: "dashboard",
      })) as { run_id?: string };
      setQuickContent("");
      setIngestSuccess("נשמר. מסיים עיבוד…");
      if (ingestRes?.run_id) {
        const first = await waitForRunCompletion(ingestRes.run_id, 8000);
        if (first.kind === "network_error") {
          setVerifyState("network_issue");
          setIngestError("Could not verify result because the status endpoint was unreachable");
          setVerifyProof("Source: run visibility endpoint not reachable");
          return;
        }
        if (first.kind === "timeout") {
          setVerifyState("processing");
          setIngestSuccess("Your content was accepted; backend processing is still running");
          setVerifyProof("Source: run state remained processing during first check");
          await new Promise((r) => setTimeout(r, 1500));
          const second = await waitForRunCompletion(ingestRes.run_id, 8000);
          if (second.kind === "network_error") {
            setVerifyState("network_issue");
            setIngestError("Could not verify result because the status endpoint was unreachable");
            setVerifyProof("Source: fallback verify check could not reach server");
            return;
          }
          if (second.kind === "timeout") {
            setVerifyState("processing");
            setIngestSuccess("Processing is still active after retry; no final outcome yet");
            setVerifyProof("Source: run state still processing after fallback retry");
            return;
          }
          const retryState = ((second.vis?.state || "").toLowerCase());
          if (retryState === "failed") {
            setVerifyState("failure");
            setIngestError("Processing completed with a blocked state that needs intervention");
            setVerifyProof("Source: run visibility returned failed");
            return;
          }
          setVerifyState("success");
          setIngestSuccess(
            retryState === "completed"
              ? "Ingest flow completed successfully and was persisted"
              : "Run resumed successfully and continues in background",
          );
          setVerifyProof(
            retryState === "completed"
              ? "Source: run visibility returned completed"
              : "Source: run visibility returned processing",
          );
          await load();
          return;
        }
        const state = (first.vis?.state || "").toLowerCase();
        if (state === "accepted" || state === "processing") {
          setVerifyState("processing");
          setIngestSuccess("Content was accepted; indexing is still in progress");
          setVerifyProof("Source: run visibility returned accepted/processing");
          return;
        }
        if (state === "failed") {
          setVerifyState("failure");
          let failureCause = "run visibility returned failed";
          try {
            const runStatus = await apiClient.getRunStatusV1(ingestRes.run_id);
            const lastError = [...(runStatus.timeline ?? [])]
              .reverse()
              .find((step) => step.error)?.error;
            if (lastError) failureCause = lastError;
          } catch {
            // best-effort only
          }
          setIngestError(`Processing failed: ${failureCause}`);
          setVerifyProof(`Source: ${failureCause}`);
          return;
        }
        setVerifyState("success");
        setIngestSuccess(
          state === "completed"
            ? "Ingest flow completed successfully and was persisted"
            : "Run resumed successfully and continues in background",
        );
        setVerifyProof(
          state === "completed"
            ? "Source: run visibility returned completed"
            : "Source: run visibility returned processing",
        );
      }
      await load();
      if (!ingestRes?.run_id) {
        setIngestSuccess(
          ingestKindHint === "task"
            ? "זוהתה משימה. התוכן עודכן ב-Recent activity ובמשימות."
            : "נשמר כמידע. התוכן עודכן ב-Recent activity.",
        );
      }
      setTimeout(() => setIngestSuccess(null), 4000);
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Ingest failed";
      setIngestError(`Ingest failed with exact cause: ${msg}`);
    } finally {
      setIngestLoading(false);
    }
  }

  async function handleSampleIngest() {
    if (!userId) return;
    setSampleIngestLoading(true);
    setIngestSuccess(null);
    setIngestError(null);
    try {
      await apiClient.ingestV1({
        tenant_id: tenantId,
        space_id: spaceId ?? "all",
        user_id: userId,
        content:
          "Hello KIRP — first test event from the dashboard (sample ingest).",
        source: "dashboard_first_run",
      });
      setIngestSuccess("Sample event sent. Refreshing…");
      await load();
      setIngestSuccess("Sample event ingested — check Recent activity below.");
      setTimeout(() => setIngestSuccess(null), 5000);
    } catch (e) {
      setIngestError(
        e instanceof Error ? e.message : "Sample ingest failed (is Kafka/API up?)",
      );
    } finally {
      setSampleIngestLoading(false);
    }
  }

  if (loading) {
    return (
      <div className="space-y-3">
        <PageSkeleton title subtitle cards={4} tableRows={5} />
        <div className="rounded-xl border border-[color:var(--color-border-subtle)] bg-surface2 px-4 py-3 text-xs text-textSoft">
          Loading dashboard data from API and event streams. If this takes more than a few seconds, the
          most likely cause is backend latency or unavailable runtime dependencies.
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-textMain">Dashboard</h1>
          <p className="text-sm text-textSoft mt-1">
            System health and real activity from your KIRP data.
          </p>
        </div>
        <ErrorState message={error} onRetry={load} />
      </div>
    );
  }

  const openTasks = tasks.filter((t) => !t.status || t.status === "pending");
  const completedTasks = tasks.filter((t) => t.status === "completed");
  const recentEvents = events.slice(0, 8);

  const services =
    health && typeof health === "object" && "services" in health
      ? ((health as any).services as Record<string, { status?: string; latency_ms?: number }>)
      : {};
  const buildVersionSha = process.env.NEXT_PUBLIC_APP_GIT_SHA?.trim() || "unknown";
  const knownVersionValues = [
    runtimeVersionSha,
    healthVersionSha,
    apiHeaderVersionSha,
    buildVersionSha,
  ].filter((v) => v && v !== "unknown");
  const versionMismatch = knownVersionValues.length > 1 && new Set(knownVersionValues).size > 1;
  const unknownRuntimeVersion =
    runtimeVersionSha === "unknown" ||
    healthVersionSha === "unknown" ||
    apiHeaderVersionSha === "unknown";

  return (
    <div className="space-y-6" suppressHydrationWarning>
      <div suppressHydrationWarning>
        <h1 className="text-2xl font-bold tracking-tight text-textMain">Dashboard</h1>
        <p className="text-sm text-textSoft mt-1">
          Live view of your tasks, activity, and system health, with causal feedback for each state transition.
        </p>
      </div>

      {usage && (
        <Card className="rounded-2xl border border-[color:var(--color-border-subtle)] bg-surface1/90 shadow-soft">
          <CardHeader className="pb-2">
            <CardTitle className="text-base text-textMain">Plan & usage</CardTitle>
            <p className="text-xs text-textSoft mt-0.5">
              Trial and billing align with Stripe Checkout from the Billing page.
            </p>
          </CardHeader>
          <CardContent className="flex flex-wrap items-center gap-4 text-sm text-textMain">
            <span>
              <span className="text-textSoft">Status: </span>
              <span className="font-medium capitalize">{usage.lifecycle}</span>
              {usage.trial_days_remaining != null && usage.lifecycle === "trial" && (
                <span className="text-textSoft">
                  {" "}
                  · {usage.trial_days_remaining}d left in trial
                </span>
              )}
              {usage.suspended && (
                <span className="ml-1 text-amber-500">(suspended)</span>
              )}
            </span>
            <span className="text-textSoft">
              Pipeline runs (recent):{" "}
              <span className="font-medium text-textMain">{usage.recent_runs_count}</span>
            </span>
            <span className="text-textSoft">
              Events in feed:{" "}
              <span className="font-medium text-textMain">{events.length}</span>
              <span className="text-[11px]"> (loaded)</span>
            </span>
            <Link
              href="/billing"
              className="ml-auto rounded-lg border border-[color:var(--color-primary)] px-3 py-1.5 text-xs font-medium text-[color:var(--color-primary)] hover:bg-surface2"
            >
              Billing & upgrade
            </Link>
          </CardContent>
        </Card>
      )}

      {events.length === 0 && (
        <Card className="rounded-2xl border border-dashed border-[color:var(--color-border-subtle)] bg-surface2/40 shadow-soft">
          <CardHeader className="pb-2">
            <CardTitle className="text-base text-textMain">No events yet</CardTitle>
            <p className="text-xs text-textSoft mt-0.5">
              {tasks.length > 0
                ? "No ingest events are visible yet, but tasks already exist. This usually means task/history data is present while event indexing is still catching up."
                : "Ingest creates your first event (Kafka → pipeline). Use the button below or type your own text in the next card."}
            </p>
          </CardHeader>
          <CardContent>
            <button
              type="button"
              onClick={() => void handleSampleIngest()}
              disabled={sampleIngestLoading || !userId}
              className="rounded-xl border border-[color:var(--color-primary)] bg-[color:var(--color-primary)] px-4 py-2 text-sm font-medium text-bg hover:opacity-90 disabled:opacity-50"
            >
              {sampleIngestLoading ? "Sending…" : "Run first test ingest"}
            </button>
          </CardContent>
        </Card>
      )}

      {/* Quick add knowledge — הוספת תוכן/משימה/אירוע */}
      <Card className="rounded-2xl border border-[color:var(--color-border-subtle)] bg-surface1/90 shadow-soft">
        <CardHeader>
          <CardTitle className="text-base text-textMain">הוסף ידע או משימה</CardTitle>
          <p className="text-xs text-textSoft mt-0.5">
            טקסט כאן ייכנס כ־event, יופיע ב־Recent activity ויוחלץ למשימות אם יש תאריך.
          </p>
        </CardHeader>
        <CardContent className="space-y-2">
          <div className="flex flex-wrap gap-2">
            <input
              type="text"
              placeholder="למשל: פגישה עם דני מחר, או רעיון לפרויקט"
              value={quickContent}
              onChange={(e) => setQuickContent(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleQuickIngest()}
              className="min-w-[200px] flex-1 rounded-xl border border-[color:var(--color-border-subtle)] bg-surface2 px-3 py-2 text-sm text-textMain placeholder:text-textSoft focus:outline-none focus:ring-2 focus:ring-[color:var(--color-primary)]"
            />
            <button
              type="button"
              onClick={handleQuickIngest}
              disabled={ingestLoading || !quickContent.trim() || !userId}
              className="rounded-xl border border-[color:var(--color-primary)] bg-[color:var(--color-primary)] px-4 py-2 text-sm font-medium text-bg hover:opacity-90 disabled:opacity-50"
            >
              {ingestLoading ? "מוסיף…" : "הוסף"}
            </button>
          </div>
          <p className="text-[11px] text-textSoft">
            זיהוי כרגע:{" "}
            <span className="font-medium text-textMain">
              {ingestKindHint === "task" ? "משימה" : "מידע"}
            </span>{" "}
            {ingestKindHint === "task"
              ? "— יופיע גם ב-Open tasks לאחר עיבוד."
              : "— יופיע ב-Recent activity (ללא יצירת משימה)."}
          </p>
          {ingestSuccess && <p className="text-xs text-green-400">{ingestSuccess}</p>}
          {ingestError && <p className="text-xs text-red-400">{ingestError}</p>}
          {verifyState && verifyProof ? (
            <p className="text-xs text-textSoft">
              Verify state: <span className="font-medium">{verifyState}</span> · {verifyProof}
            </p>
          ) : null}
        </CardContent>
      </Card>

      <div className="bento-grid">
        {/* Open Tasks */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <ListChecks className="h-4 w-4 text-primary" />
              Open tasks
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-semibold mb-2">{openTasks.length}</p>
            <p className="text-sm text-textSoft mb-3">
              {completedTasks.length} completed • {tasks.length} total
            </p>
            <ul className="space-y-1 text-sm text-textMain max-h-40 overflow-auto">
              {openTasks.slice(0, 5).map((t) => (
                <li key={t.id} className="flex justify-between gap-2">
                  <span className="truncate">{t.title}</span>
                  <span className="text-[11px] text-textSoft">
                    {t.due_date ? formatUtcDate(t.due_date) : ""}
                  </span>
                </li>
              ))}
              {openTasks.length === 0 && (
                <li className="text-sm text-textSoft">No open tasks. Great job.</li>
              )}
            </ul>
          </CardContent>
        </Card>

        {/* Recent Activity */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Activity className="h-4 w-4 text-primary" />
              Recent activity
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-1 text-sm max-h-40 overflow-auto">
              {recentEvents.map((e) => (
                <li key={e.id} className="flex flex-col">
                  <span className="text-textMain truncate">
                    {e.topic || e.source || "Event"}
                  </span>
                  <span className="text-[11px] text-textSoft">
                    {formatUtcDateTime(e.timestamp)} • {e.source}
                  </span>
                </li>
              ))}
              {recentEvents.length === 0 && (
                <li className="text-sm text-textSoft">
                  {tasks.length > 0 || hasHistory
                    ? "No ingest events are visible in this feed yet. Activity exists in Tasks/History, so this is likely indexing delay or event feed filtering."
                    : "No recent events."}
                </li>
              )}
            </ul>
          </CardContent>
        </Card>

        {/* System Health */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <HeartPulse className="h-4 w-4 text-primary" />
              System health
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm mb-3">
              Status:{" "}
              <span className="font-semibold">
                {(health as any)?.status ?? "unknown"}
              </span>
            </p>
            <p className="text-xs text-textSoft mb-3">
              Version:{" "}
              <span className="font-mono text-textMain">
                {runtimeVersionSha === "unknown"
                  ? "unknown"
                  : `${runtimeVersionSha.slice(0, 7)} (${runtimeVersionSha})`}
              </span>
            </p>
            <p className="text-xs text-textSoft mb-3">
              Trust score:{" "}
              <span className="font-mono text-textMain">{trustScore}/100</span>
              {trustReasons.length > 0 ? (
                <span className="text-amber-400">
                  {" "}
                  · {trustReasons.join(", ")}
                </span>
              ) : null}
            </p>
            <p className="text-xs text-textSoft mb-3">
              Active auto-rules:{" "}
              <span className="font-mono text-textMain">
                {activeAutoRules.length > 0 ? activeAutoRules.join(", ") : "none"}
              </span>
            </p>
            <p className="text-xs text-textSoft mb-3">
              Current blockers:{" "}
              <span className="font-mono text-textMain">
                {currentBlockers.length > 0 ? currentBlockers.join(", ") : "none"}
              </span>
            </p>
            <p className="text-xs text-textSoft mb-3">
              Unknown states:{" "}
              <span className="font-mono text-textMain">
                {unknownStates.length > 0 ? unknownStates.join(", ") : "none"}
              </span>
            </p>
            <p className="text-xs text-textSoft mb-3">
              Build time: <span className="font-mono text-textMain">{runtimeBuildTime}</span> ·
              Environment: <span className="font-mono text-textMain"> {runtimeEnvironment}</span>
            </p>
            <p className="text-xs text-textSoft mb-3">
              Sources: health=<span className="font-mono text-textMain">{healthVersionSha}</span> ·
              api_header=<span className="font-mono text-textMain">{apiHeaderVersionSha}</span> ·
              ui_build=<span className="font-mono text-textMain">{buildVersionSha}</span>
            </p>
            {versionMismatch || unknownRuntimeVersion ? (
              <p className="text-xs text-amber-400 mb-3">
                Runtime warning:{" "}
                {unknownRuntimeVersion
                  ? "runtime version is missing in at least one source. Fix: set APP_GIT_SHA in API/container and NEXT_PUBLIC_APP_GIT_SHA in dashboard build env."
                  : "version mismatch detected between health, API header, and UI build."}
              </p>
            ) : null}
            {authFailureSpike ? (
              <p className="text-xs text-amber-400 mb-3">
                Runtime warning: repeated auth failures detected in the recent window.
              </p>
            ) : null}
            <ul className="space-y-1 text-sm max-h-40 overflow-auto">
              {Object.entries(services).map(([name, svc]) => (
                <li key={name} className="flex justify-between gap-2">
                  <span className="capitalize text-textMain">{name}</span>
                  <span className="text-[11px] text-textSoft">
                    {svc.status ?? "unknown"}{" "}
                    {typeof svc.latency_ms === "number"
                      ? `· ${Math.round(svc.latency_ms)} ms`
                      : ""}
                  </span>
                </li>
              ))}
              {Object.keys(services).length === 0 && (
                <li className="text-sm text-textSoft">No health data.</li>
              )}
            </ul>
          </CardContent>
        </Card>

        {/* Today’s Insight */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Database className="h-4 w-4 text-primary" />
              Today&apos;s insight
            </CardTitle>
          </CardHeader>
          <CardContent>
            {insight ? (
              <div className="space-y-2 text-sm">
                <p className="text-textMain whitespace-pre-wrap">
                  {insight.answer}
                </p>
              </div>
            ) : (
              <p className="text-sm text-textSoft">
                No insight was generated because recent evidence is still too sparse. Add knowledge or tasks to
                trigger a grounded recommendation with explicit source context.
              </p>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

export default function DashboardPage() {
  return (
    <Suspense fallback={<PageSkeleton title subtitle cards={4} tableRows={5} />}>
      <RealDashboardContent />
    </Suspense>
  );
}
