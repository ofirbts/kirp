"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { apiClient } from "@/lib/apiClient";

interface ServiceRow {
  name: string;
  status: string;
  url?: string;
  latency_ms?: number;
}

const OPTIONAL_SERVICES = ["brand_os_api", "brand_os_monitoring", "kafka"];

const PORTS = [
  { port: 8000, service: "KIRP API" },
  { port: 8001, service: "Monitoring" },
  { port: 8002, service: "Brand OS API" },
  { port: 3100, service: "KIRP UI" },
  { port: 8501, service: "Streamlit" },
  { port: 6333, service: "Qdrant" },
  { port: 6379, service: "Redis" },
  { port: 5432, service: "Postgres" },
  { port: 8081, service: "Mongo Express" },
  { port: 9090, service: "Prometheus" },
  { port: 8181, service: "OPA" },
];

function serviceStatus(s: { status?: string }): string {
  const v = s?.status;
  if (v === "ok" || v === "healthy") return "healthy";
  if (v === "error" || v === "unavailable" || v === "down") return "down";
  return v ?? "unknown";
}

export default function MissionControlPage() {
  const [services, setServices] = useState<ServiceRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [errors, setErrors] = useState<string[]>([]);

  useEffect(() => {
    apiClient
      .getObservabilityHealth()
      .then((d) => {
        const raw = (d as { services?: Record<string, { status?: string; latency_ms?: number }> })?.services ?? {};
        const list: ServiceRow[] = Object.entries(raw).map(([name, v]) => ({
          name,
          status: serviceStatus(v ?? {}),
          latency_ms: typeof (v as { latency_ms?: number })?.latency_ms === "number" ? (v as { latency_ms: number }).latency_ms : undefined,
        }));
        setServices(list);
        const down = list.filter((s) => s.status !== "healthy");
        const critical = down.filter((s) => !OPTIONAL_SERVICES.includes(s.name));
        setErrors(critical.map((s) => `${s.name} is ${s.status}`));
      })
      .catch(() => setErrors(["Backend unreachable. Set NEXT_PUBLIC_API_URL to your API."]))
      .finally(() => setLoading(false));
  }, []);

  const healthy = services.filter((s) => s.status === "healthy").length;
  const total = services.length;

  return (
    <div className="space-y-6" suppressHydrationWarning>
      <div suppressHydrationWarning>
        <h1 className="text-2xl font-bold tracking-tight text-neutral-100">Mission Control</h1>
        <p className="mt-1 text-sm text-muted-foreground">System health, ports, and activity.</p>
      </div>
      <section className="grid gap-6 md:grid-cols-2" suppressHydrationWarning>
        <div className="rounded-lg border border-neutral-800 bg-neutral-900/70 p-6 shadow-sm" suppressHydrationWarning>
          <h2 className="text-lg font-semibold text-neutral-100">System Health</h2>
          {loading ? (
            <p className="mt-2 text-sm text-neutral-400">Loading...</p>
          ) : (
            <>
              <p className="mt-2 text-sm text-neutral-400">
                <span className="font-medium text-cyan-400">{healthy}</span> / {total} services healthy
              </p>
              <ul className="mt-4 space-y-2">
                {services.map((s) => (
                  <li key={s.name} className="flex items-center gap-2">
                    <span className={s.status === "healthy" ? "text-green-500" : "text-red-500"}>
                      {s.status === "healthy" ? "OK" : "X"}
                    </span>
                    <span className="text-neutral-300">{s.name}</span>
                    {s.latency_ms != null && (
                      <span className="text-xs text-neutral-500">{Math.round(s.latency_ms)}ms</span>
                    )}
                  </li>
                ))}
              </ul>
            </>
          )}
        </div>
        <div className="rounded-lg border border-neutral-800 bg-neutral-900/70 p-6 shadow-sm" suppressHydrationWarning>
          <h2 className="text-lg font-semibold text-neutral-100">Port Map</h2>
          <ul className="mt-4 space-y-2">
            {PORTS.map((p) => (
              <li key={p.port} className="flex justify-between text-sm text-neutral-300">
                <span>{p.service}</span>
                <span className="font-mono">{p.port}</span>
              </li>
            ))}
          </ul>
        </div>
      </section>
      <section className="rounded-lg border border-neutral-800 bg-neutral-900/70 p-6 shadow-sm" suppressHydrationWarning>
        <h2 className="text-lg font-semibold text-neutral-100">Error Center</h2>
        {errors.length === 0 ? (
          <p className="mt-2 text-sm text-neutral-400">No errors reported.</p>
        ) : (
          <ul className="mt-2 list-disc list-inside text-amber-400">
            {errors.map((e, i) => (
              <li key={i}>{e}</li>
            ))}
          </ul>
        )}
      </section>
      <div className="flex gap-4">
        <Link href="/system-control" className="font-medium text-cyan-400 hover:underline">System Control</Link>
        <Link href="/run" className="font-medium text-cyan-400 hover:underline">Run Pipeline</Link>
      </div>
    </div>
  );
}
