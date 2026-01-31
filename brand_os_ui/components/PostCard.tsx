interface PostCardProps {
  headline: string;
  body: string;
  hook_used?: string;
  cta_used?: string;
  status?: string;
  trace_id?: string;
}

export default function PostCard({ headline, body, hook_used, cta_used, status, trace_id }: PostCardProps) {
  return (
    <div className="bg-white rounded-lg shadow p-4 border border-neutral-100">
      {trace_id && <p className="text-xs text-neutral-200 mb-1">{trace_id}</p>}
      {status && (
        <span className={`text-xs px-2 py-0.5 rounded ${status === "approved" ? "bg-secondary/20 text-primary" : "bg-accent/20 text-primary"}`}>
          {status}
        </span>
      )}
      <h3 className="font-semibold text-primary mt-2">{headline}</h3>
      {hook_used && <p className="text-sm text-neutral-200 italic mt-1">{hook_used}</p>}
      <p className="mt-2 text-sm whitespace-pre-wrap">{body}</p>
      {cta_used && <p className="mt-2 text-secondary font-medium">{cta_used}</p>}
    </div>
  );
}
