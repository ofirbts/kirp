"use client";

import { useEffect, useState } from "react";
import PostCard from "@/components/PostCard";

interface HistoryEntry {
  trace_id?: string;
  tenant_id?: string;
  platform?: string;
  topic_hint?: string;
  body_hash?: string;
  published_at?: string;
  status?: string;
}

export default function HistoryPage() {
  const [entries, setEntries] = useState<HistoryEntry[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch("/api/history")
      .then((r) => r.json())
      .then((data) => setEntries(Array.isArray(data) ? data : []))
      .catch(() => setError("Could not load history. Use Content Memory Log or run API."));
  }, []);

  if (error) return <p className="text-accent">{error}</p>;
  return (
    <div>
      <h1 className="text-2xl font-bold text-primary">History</h1>
      <p className="mt-2 text-neutral-200">Past runs from Content Memory Log.</p>
      <div className="mt-6 grid gap-4 md:grid-cols-2">
        {entries.map((e, i) => (
          <PostCard
            key={e.trace_id || i}
            headline={e.topic_hint || "Run"}
            body={`Platform: ${e.platform || "-"} · ${e.published_at || ""}`}
            status={e.status}
            trace_id={e.trace_id}
          />
        ))}
      </div>
      {entries.length === 0 && !error && <p className="mt-4 text-neutral-200">No history entries. Run the pipeline to populate.</p>}
    </div>
  );
}
