"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

interface PortRow {
  port: number;
  pid?: string;
  command?: string;
}

interface ContainerRow {
  name: string;
  status: string;
  ports: string;
}

export default function SystemControlPage() {
  const [ports, setPorts] = useState<PortRow[]>([]);
  const [containers, setContainers] = useState<ContainerRow[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      fetch("/api/system/ports").then((r) => r.json()).then((d) => setPorts(d.ports || [])).catch(() => setPorts([])),
      fetch("/api/system/containers").then((r) => r.json()).then((d) => setContainers(d.containers || [])).catch(() => setContainers([])),
    ]).finally(() => setLoading(false));
  }, []);

  const keyPorts = [8000, 8001, 8002, 3000, 8501, 6333, 6379, 5432, 8081, 9090, 8181];

  return (
    <div className="space-y-6" suppressHydrationWarning>
      <div suppressHydrationWarning>
        <h1 className="text-2xl font-bold tracking-tight text-neutral-100">System Control Center</h1>
        <p className="mt-1 text-sm text-muted-foreground">Port scanner, Docker control. Use START.sh for full control.</p>
      </div>
      <section className="rounded-lg border border-neutral-800 bg-neutral-900/70 p-6 shadow-sm">
        <h2 className="text-lg font-semibold text-neutral-100">Port Scanner</h2>
        <p className="mt-1 text-sm text-neutral-400">Key ports: {keyPorts.join(", ")}.</p>
        {loading ? (
          <p className="mt-4 text-sm text-neutral-400">Loading...</p>
        ) : ports.length > 0 ? (
          <table className="mt-4 w-full text-sm">
            <thead>
              <tr className="border-b border-neutral-700">
                <th className="py-2 text-left text-neutral-400">Port</th>
                <th className="py-2 text-left text-neutral-400">PID</th>
                <th className="py-2 text-left text-neutral-400">Command</th>
              </tr>
            </thead>
            <tbody>
              {ports.map((p, i) => (
                <tr key={i} className="border-b border-neutral-800">
                  <td className="py-2 text-neutral-300">{p.port}</td>
                  <td className="py-2 text-neutral-400">{p.pid || "—"}</td>
                  <td className="py-2 font-mono text-neutral-400">{p.command || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p className="mt-4 text-sm text-neutral-400">No port data.</p>
        )}
      </section>
      <section className="rounded-lg border border-neutral-800 bg-neutral-900/70 p-6 shadow-sm">
        <h2 className="text-lg font-semibold text-neutral-100">Docker Containers</h2>
        {containers.length > 0 ? (
          <table className="mt-4 w-full text-sm">
            <thead>
              <tr className="border-b border-neutral-700">
                <th className="py-2 text-left text-neutral-400">Name</th>
                <th className="py-2 text-left text-neutral-400">Status</th>
                <th className="py-2 text-left text-neutral-400">Ports</th>
              </tr>
            </thead>
            <tbody>
              {containers.map((c, i) => (
                <tr key={i} className="border-b border-neutral-800">
                  <td className="py-2 text-neutral-300">{c.name}</td>
                  <td className="py-2 text-neutral-400">{c.status}</td>
                  <td className="py-2 font-mono text-xs text-neutral-400">{c.ports}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p className="mt-4 text-sm text-neutral-400">No container data.</p>
        )}
      </section>
      <section className="rounded-lg border border-neutral-800 bg-neutral-900/70 p-6 shadow-sm">
        <h2 className="text-lg font-semibold text-neutral-100">Quick Actions</h2>
        <ul className="mt-4 space-y-2 text-sm text-neutral-400">
          <li><strong className="text-neutral-300">Fix port:</strong> <code className="rounded bg-neutral-800 px-1">./scripts/kill_port.sh 8000</code></li>
          <li><strong className="text-neutral-300">Restart:</strong> <code className="rounded bg-neutral-800 px-1">./scripts/restart_service.sh kirp-api</code></li>
          <li><strong className="text-neutral-300">Status:</strong> <code className="rounded bg-neutral-800 px-1">./START.sh</code></li>
        </ul>
      </section>
      <div>
        <Link href="/mission-control" className="font-medium text-cyan-400 hover:underline">← Mission Control</Link>
      </div>
    </div>
  );
}
