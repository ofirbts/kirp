"use client";

import { useEffect, useState } from "react";
import VisualCard from "@/components/VisualCard";

interface VisualEntry {
  trace_id?: string;
  image_prompt: string;
  aspect_ratio?: string;
  format?: string;
  alt_text?: string;
}

export default function VisualsPage() {
  const [visuals, setVisuals] = useState<VisualEntry[]>([]);

  useEffect(() => {
    fetch("/api/visuals")
      .then((r) => r.json())
      .then((data) => setVisuals(Array.isArray(data) ? data : []))
      .catch(() => setVisuals([]));
  }, []);

  return (
    <div>
      <h1 className="text-2xl font-bold text-primary">Visuals</h1>
      <p className="mt-2 text-neutral-200">Generated visual prompts from runs.</p>
      <div className="mt-6 grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {visuals.map((v, i) => (
          <VisualCard
            key={v.trace_id || i}
            image_prompt={v.image_prompt}
            aspect_ratio={v.aspect_ratio}
            format={v.format}
            alt_text={v.alt_text}
            trace_id={v.trace_id}
          />
        ))}
      </div>
      {visuals.length === 0 && (
        <p className="mt-4 text-neutral-200">No visuals yet. Run the pipeline to generate visual specs.</p>
      )}
    </div>
  );
}
