"use client";

interface VisualCardProps {
  image_prompt: string;
  aspect_ratio?: string;
  format?: string;
  alt_text?: string;
  trace_id?: string;
}

export default function VisualCard({
  image_prompt,
  aspect_ratio,
  format,
  alt_text,
  trace_id,
}: VisualCardProps) {
  return (
    <div className="rounded-lg border border-neutral-800 bg-neutral-900/70 p-4 shadow-sm">
      {trace_id && (
        <p className="mb-1 text-xs text-neutral-500">{trace_id}</p>
      )}
      <div className="flex aspect-video items-center justify-center rounded bg-neutral-800 text-sm text-neutral-500">
        Placeholder (prompt below)
      </div>
      <p className="mt-2 font-medium text-neutral-200">Prompt</p>
      <p className="mt-1 text-sm text-neutral-400">{image_prompt}</p>
      <div className="mt-2 flex gap-2 text-xs text-neutral-500">
        {aspect_ratio && <span>{aspect_ratio}</span>}
        {format && <span>{format}</span>}
        {alt_text && (
          <span title={alt_text}>Alt: {alt_text.slice(0, 40)}…</span>
        )}
      </div>
    </div>
  );
}
