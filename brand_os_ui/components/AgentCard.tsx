interface AgentCardProps {
  id: string;
  name: string;
  role?: string;
  phase?: string;
}

export default function AgentCard({ id, name, role, phase }: AgentCardProps) {
  return (
    <div className="bg-white rounded-lg shadow p-4 border border-neutral-100">
      <h3 className="font-semibold text-primary">{name}</h3>
      <p className="text-xs text-neutral-200 mt-1">{id}</p>
      {phase && <span className="text-xs px-2 py-0.5 rounded bg-secondary/20 text-primary mt-2 inline-block">{phase}</span>}
      {role && <p className="mt-2 text-sm text-neutral-200">{role}</p>}
    </div>
  );
}
