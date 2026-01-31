"use client";

import { useEffect, useState } from "react";
import { healthCheck } from "@/lib/api";
import PostCard from "@/components/PostCard";
import Link from "next/link";

interface MemEntry {
  trace_id?: string;
  tenant_id?: string;
  platform?: string;
  topic_hint?: string;
  status?: string;
  published_at?: string;
}

export default function DashboardPage() {
  const [health, setHealth] = useState<{ status: string } | null>(null);
  const [runs, setRuns] = useState<MemEntry[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    healthCheck()
      .then(setHealth)
      .catch((e) => setError(e.message));
  }, []);

  return (
    <div>
      <h1 className="text-2xl font-bold text-primary">Dashboard</h1>
      <div className="mt-4 flex gap-4 items-center">
        <span className="text-sm text-neutral-200">API:</span>
        {health ? (
          <span className="text-secondary font-medium">{health.status}</span>
        ) : error ? (
          <span className="text-accent">{error}</span>
        ) : (
          <span className="text-neutral-200">Checking…</span>
        )}
        <Link href="/run" className="text-secondary hover:underline">Run pipeline</Link>
      </div>
      <section className="mt-8">
        <h2 className="text-lg font-semibold text-primary">Latest runs</h2>
        <p className="text-sm text-neutral-200 mt-1">Runs appear in History after execution. Trigger a run from the Run page.</p>
        {runs.length === 0 && (
          <p className="mt-4 text-neutral-200">No runs loaded. Run the pipeline or load history.</p>
        )}
        <div className="mt-4 grid gap-4 md:grid-cols-2">
          {runs.slice(0, 6).map((r, i) => (
            <PostCard
              key={r.trace_id || i}
              headline={r.topic_hint || "Run"}
              body={`${r.platform || ""} · ${r.status || ""}`}
              status={r.status}
              trace_id={r.trace_id}
            />
          ))}
        </div>
      </section>
    </div>
  );
}
