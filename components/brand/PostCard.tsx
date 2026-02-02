"use client";

interface PostCardProps {
  headline: string;
  body: string;
  hook_used?: string;
  cta_used?: string;
  status?: string;
  trace_id?: string;
}

export default function PostCard({
  headline,
  body,
  hook_used,
  cta_used,
  status,
  trace_id,
}: PostCardProps) {
  return (
    <div className="rounded-lg border border-neutral-800 bg-neutral-900/70 p-4 shadow-sm">
      {trace_id && <p className="mb-1 text-xs text-neutral-500">{trace_id}</p>}
      {status && (
        <span
          className={
            status === "approved"
              ? "rounded bg-cyan-500/20 px-2 py-0.5 text-xs text-cyan-300"
              : "rounded bg-amber-500/20 px-2 py-0.5 text-xs text-amber-300"
          }
        >
          {status}
        </span>
      )}
      <h3 className="mt-2 font-semibold text-neutral-100">{headline}</h3>
      {hook_used && (
        <p className="mt-1 text-sm italic text-neutral-400">{hook_used}</p>
      )}
      <p className="mt-2 whitespace-pre-wrap text-sm text-neutral-300">
        {body}
      </p>
      {cta_used && (
        <p className="mt-2 font-medium text-cyan-400">{cta_used}</p>
      )}
    </div>
  );
}
