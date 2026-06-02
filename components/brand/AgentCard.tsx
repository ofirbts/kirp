"use client";

interface AgentCardProps {
  id: string;
  name: string;
  role?: string;
  phase?: string;
}

export default function AgentCard({ id, name, role, phase }: AgentCardProps) {
  return (
    <div className="rounded-lg border border-neutral-800 bg-neutral-900/70 p-4 shadow-sm">
      <h3 className="font-semibold text-neutral-100">{name}</h3>
      <p className="mt-1 text-xs text-neutral-500">{id}</p>
      {phase && (
        <span className="mt-2 inline-block rounded bg-cyan-500/20 px-2 py-0.5 text-xs text-cyan-300">
          {phase}
        </span>
      )}
      {role && <p className="mt-2 text-sm text-neutral-400">{role}</p>}
    </div>
  );
}
