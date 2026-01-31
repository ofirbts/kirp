"use client";

import { useEffect, useState } from "react";
import AgentCard from "@/components/AgentCard";

interface AgentDef {
  id: string;
  name: string;
  role?: string;
  phase?: string;
}

export default function AgentsPage() {
  const [agents, setAgents] = useState<AgentDef[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch("/api/agents")
      .then((r) => r.json())
      .then((data) => setAgents(Array.isArray(data) ? data : []))
      .catch(() => setError("Could not load agents. Ensure API or static data is available."));
  }, []);

  if (error) return <p className="text-accent">{error}</p>;
  const defaultAgents: AgentDef[] = [
    { id: "CONTEXT_SCANNER", name: "Context Scanner", phase: "context", role: "Scan and synthesize world context." },
    { id: "STRATEGIC_PLANNER", name: "Strategic Planner", phase: "strategy", role: "Turn context into strategy brief." },
    { id: "TECHNICAL_STORYTELLER", name: "Technical Storyteller", phase: "creation", role: "Draft first version." },
    { id: "HUMAN_EDGE", name: "Human Edge", phase: "creation", role: "Polish for clarity and platform-native feel." },
    { id: "IDENTITY_GUARDIAN", name: "Identity Guardian", phase: "quality", role: "Gatekeeper: identity and tone." },
    { id: "SKEPTICAL_CTO", name: "Skeptical CTO", phase: "quality", role: "Gatekeeper: technical accuracy." },
    { id: "VISUAL_GENERATOR", name: "Visual Generator", phase: "distribution", role: "Produce visual spec." },
    { id: "GROWTH_ANALYST", name: "Growth Analyst", phase: "distribution", role: "Recommendations." },
  ];
  const list = agents.length ? agents : defaultAgents;
  return (
    <div>
      <h1 className="text-2xl font-bold text-primary">Agents</h1>
      <p className="mt-2 text-neutral-200">Agent definitions from brand_os_v3/agents/.</p>
      <div className="mt-6 grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {list.map((a) => (
          <AgentCard key={a.id} id={a.id} name={a.name} role={a.role} phase={a.phase} />
        ))}
      </div>
    </div>
  );
}
