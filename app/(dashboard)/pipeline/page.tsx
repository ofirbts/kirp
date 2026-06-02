"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import AgentCard from "@/components/brand/AgentCard";
import { apiClient } from "@/lib/apiClient";
import type { Agent } from "@/lib/types";

const NODES = [
  "Context Scanner",
  "Strategic Planner",
  "Technical Storyteller",
  "Human Edge",
  "Identity Guardian",
  "Skeptical CTO",
  "Visual Generator",
  "Growth Analyst",
];

const AGENTS = [
  { id: "CONTEXT_SCANNER", name: "Context Scanner", phase: "context", role: "Scan and synthesize world context." },
  { id: "STRATEGIC_PLANNER", name: "Strategic Planner", phase: "strategy", role: "Turn context into strategy brief." },
  { id: "TECHNICAL_STORYTELLER", name: "Technical Storyteller", phase: "creation", role: "Draft first version." },
  { id: "HUMAN_EDGE", name: "Human Edge", phase: "creation", role: "Polish for clarity and platform-native feel." },
  { id: "IDENTITY_GUARDIAN", name: "Identity Guardian", phase: "quality", role: "Gatekeeper: identity and tone." },
  { id: "SKEPTICAL_CTO", name: "Skeptical CTO", phase: "quality", role: "Gatekeeper: technical accuracy." },
  { id: "VISUAL_GENERATOR", name: "Visual Generator", phase: "distribution", role: "Produce visual spec." },
  { id: "GROWTH_ANALYST", name: "Growth Analyst", phase: "distribution", role: "Recommendations." },
];

export default function PipelinePage() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadAgents = async () => {
    setLoading(true);
    setError(null);
    try {
      const r = await apiClient.listAgents();
      setAgents(r.data ?? []);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load agents");
      setAgents([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAgents();
  }, []);

  return (
    <div className="space-y-6" suppressHydrationWarning>
      <div suppressHydrationWarning>
        <h1 className="text-2xl font-bold tracking-tight text-neutral-100">Pipeline Visualizer</h1>
        <p className="mt-1 text-sm text-muted-foreground">Orchestration flow and pipeline agents.</p>
      </div>
      <section className="rounded-lg border border-neutral-800 bg-neutral-900/70 p-6">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-neutral-100">Active KIRP Agents (real data)</h2>
          <button
            type="button"
            onClick={loadAgents}
            disabled={loading}
            className="text-sm text-cyan-400 hover:underline disabled:opacity-50"
          >
            Refresh
          </button>
        </div>
        {error ? (
          <p className="mt-4 text-sm text-amber-400">{error}</p>
        ) : loading ? (
          <p className="mt-4 text-sm text-neutral-400">Loading…</p>
        ) : agents.length > 0 ? (
          <div className="mt-4 flex flex-wrap gap-2">
            {agents.map((a) => (
              <span
                key={a.id}
                className="rounded bg-cyan-500/20 px-3 py-2 text-sm text-cyan-300"
                title={a.description}
              >
                {a.name} ({a.type})
              </span>
            ))}
          </div>
        ) : (
          <p className="mt-4 text-sm text-neutral-400">No agents returned from API.</p>
        )}
      </section>
      <div className="flex flex-wrap gap-2">
        {NODES.map((n) => (
          <span key={n} className="rounded bg-cyan-500/20 px-3 py-2 text-sm text-cyan-300">{n}</span>
        ))}
      </div>
      <div>
        <h2 className="text-lg font-semibold text-neutral-100">Pipeline Agents</h2>
        <div className="mt-4 grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {AGENTS.map((a) => (
            <AgentCard key={a.id} id={a.id} name={a.name} role={a.role} phase={a.phase} />
          ))}
        </div>
      </div>
      <div>
        <Link href="/mission-control" className="font-medium text-cyan-400 hover:underline">← Mission Control</Link>
      </div>
    </div>
  );
}
