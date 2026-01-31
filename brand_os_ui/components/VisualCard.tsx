interface VisualCardProps {
  image_prompt: string;
  aspect_ratio?: string;
  format?: string;
  alt_text?: string;
  trace_id?: string;
}

export default function VisualCard({ image_prompt, aspect_ratio, format, alt_text, trace_id }: VisualCardProps) {
  return (
    <div className="bg-white rounded-lg shadow p-4 border border-neutral-100">
      {trace_id && <p className="text-xs text-neutral-200 mb-1">{trace_id}</p>}
      <div className="aspect-video bg-neutral-100 rounded flex items-center justify-center text-neutral-200 text-sm">
        Placeholder (prompt below)
      </div>
      <p className="mt-2 text-sm text-primary font-medium">Prompt</p>
      <p className="text-sm text-neutral-200 mt-1">{image_prompt}</p>
      <div className="flex gap-2 mt-2 text-xs text-neutral-200">
        {aspect_ratio && <span>{aspect_ratio}</span>}
        {format && <span>{format}</span>}
        {alt_text && <span title={alt_text}>Alt: {alt_text.slice(0, 40)}…</span>}
      </div>
    </div>
  );
}
