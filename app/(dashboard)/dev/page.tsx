"use client";

import { useState } from "react";
import Link from "next/link";

export default function DevPage() {
  const [input, setInput] = useState("{}");
  const [output, setOutput] = useState("");
  const [loading, setLoading] = useState(false);

  const apiBase = process.env.NEXT_PUBLIC_BRAND_OS_API_URL || "http://127.0.0.1:8002";

  const runApi = () => {
    setLoading(true);
    let payload: Record<string, string> = {
      tenant_id: "t1",
      platform: "linkedin",
      topic_hint: "API release",
    };
    try {
      const parsed = JSON.parse(input);
      if (typeof parsed === "object" && parsed !== null) payload = { ...payload, ...parsed };
    } catch {
      // use default
    }
    fetch(apiBase + "/brand-os/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    })
      .then((r) => r.json().then((d) => setOutput(JSON.stringify(r.ok ? d : { status: r.status, ...d }, null, 2))))
      .catch((e) => {
        const msg = e.message || String(e);
        const unreachable = msg.includes("Failed to fetch") || msg.includes("Connection refused") || msg.includes("NetworkError");
        setOutput(unreachable ? "Error: Brand OS API not running. Start on port 8002 or set NEXT_PUBLIC_BRAND_OS_API_URL." : "Error: " + msg);
      })
      .finally(() => setLoading(false));
  };

  return (
    <div className="space-y-6" suppressHydrationWarning>
      <div suppressHydrationWarning>
        <h1 className="text-2xl font-bold tracking-tight text-neutral-100">Developer Mode</h1>
        <p className="mt-1 text-sm text-muted-foreground">API Explorer, Agent Debugger, Workflow Editor, Event Stream.</p>
      </div>
      <section className="rounded-lg border border-neutral-800 bg-neutral-900/70 p-6 shadow-sm">
        <h2 className="text-lg font-semibold text-neutral-100">API Explorer</h2>
        <p className="mt-2 text-sm text-neutral-400">POST /brand-os/run. Edit JSON (optional) and Run.</p>
        <textarea
          className="mt-4 h-24 w-full rounded border border-neutral-700 bg-neutral-900 p-3 font-mono text-sm text-neutral-100"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder='{"tenant_id":"t1","platform":"linkedin","topic_hint":"API release"}'
        />
        <button
          type="button"
          onClick={runApi}
          disabled={loading}
          className="mt-4 rounded bg-cyan-600 px-4 py-2 font-medium text-white hover:bg-cyan-500 disabled:opacity-50"
        >
          {loading ? "Running..." : "Run"}
        </button>
        {output && (
          <pre className="mt-4 max-h-96 overflow-auto rounded bg-neutral-800 p-4 text-sm text-neutral-300">
            {output}
          </pre>
        )}
      </section>
      <section className="rounded-lg border border-neutral-800 bg-neutral-900/70 p-6 shadow-sm">
        <h2 className="text-lg font-semibold text-neutral-100">OpenAPI / Swagger</h2>
        <a href={apiBase + "/docs"} target="_blank" rel="noopener noreferrer" className="font-medium text-cyan-400 hover:underline">
          {apiBase}/docs
        </a>
      </section>
      <section className="rounded-lg border border-neutral-800 bg-neutral-900/70 p-6 shadow-sm">
        <h2 className="text-lg font-semibold text-neutral-100">Agent Debugger</h2>
        <p className="mt-2 text-sm text-neutral-400">Run any agent with custom input. Wire to backend when agent playground API exists.</p>
      </section>
      <section className="rounded-lg border border-neutral-800 bg-neutral-900/70 p-6 shadow-sm">
        <h2 className="text-lg font-semibold text-neutral-100">Event Stream</h2>
        <p className="mt-2 text-sm text-neutral-400">Kafka / event logs. Filter by topic, tenant, type.</p>
      </section>
      <div suppressHydrationWarning>
        <Link href="/mission-control" className="font-medium text-cyan-400 hover:underline">Back to Mission Control</Link>
      </div>
    </div>
  );
}
