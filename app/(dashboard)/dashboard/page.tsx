"use client";

import React, { useEffect, useState, Suspense } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { StatsCard } from "@/components/ui/stats-card";
import { EventRateChart } from "@/components/data/EventRateChart";
import { RadialChart } from "@/components/charts/RadialChart";
import { DataTable } from "@/components/dashboard/DataTable";
import { PageSkeleton } from "@/components/dashboard/PageSkeleton";
import { ErrorState } from "@/components/feedback/ErrorState";
import { apiClient } from "@/lib/apiClient";
import type { Event, Agent } from "@/lib/types";
import { Activity, Cpu, Database, Zap } from "lucide-react";

function DashboardContent() {
  const [stats, setStats] = useState<Record<string, unknown> | null>(null);
  const [events, setEvents] = useState<Event[]>([]);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = React.useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [statsRes, eventsRes, agentsRes] = await Promise.all([
        apiClient.getStats().catch(() => ({})),
        apiClient.listEvents({}).then((r) => r.data ?? []),
        apiClient.listAgents({}).then((r) => r.data ?? []),
      ]);
      setStats(statsRes as Record<string, unknown>);
      setEvents(eventsRes);
      setAgents(agentsRes);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load dashboard");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

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
  const newInsights = typeof stats?.new_insights === "number" ? stats.new_insights : 0;
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
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Dashboard</h1>
        <p className="text-muted-foreground text-sm mt-1">
          System health, KPIs, and overview.
        </p>
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
          keyExtractor={(r) => r.id}
          columns={[
            { key: "topic", header: "Topic", render: (r) => r.topic || "—" },
            { key: "severity", header: "Severity", render: (r) => r.severity },
            { key: "timestamp", header: "Time", render: (r) => r.timestamp?.slice(0, 19) ?? "—" },
          ]}
          emptyMessage="No recent events."
          pageSize={10}
        />
        <DataTable<Agent>
          title="Active agents"
          data={agents}
          keyExtractor={(r) => r.id}
          columns={[
            { key: "name", header: "Name", render: (r) => r.name },
            { key: "type", header: "Type", render: (r) => r.type },
            { key: "status", header: "Status", render: (r) => r.status },
          ]}
          emptyMessage="No agents."
          pageSize={10}
        />
      </div>
    </div>
  );
}

export default function DashboardPage() {
  return (
    <Suspense fallback={<PageSkeleton title subtitle cards={4} tableRows={5} />}>
      <DashboardContent />
    </Suspense>
  );
}
