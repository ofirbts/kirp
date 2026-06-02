"use client";

import { useEffect, useState, useCallback } from "react";
import VisualCard from "@/components/brand/VisualCard";
import { ErrorState } from "@/components/feedback/ErrorState";
import { apiClient } from "@/lib/apiClient";
import { DEFAULT_TENANT_ID } from "@/lib/constants";
import { useTenantContextStore } from "@/lib/stores/tenantContextStore";

interface VisualEntry {
  id?: string;
  trace_id?: string;
  name?: string;
  image_prompt?: string;
  aspect_ratio?: string;
  format?: string;
  alt_text?: string;
  chartType?: string;
  config?: Record<string, unknown>;
}

export default function VisualsPage() {
  const { tenantId, spaceId } = useTenantContextStore();
  const [visuals, setVisuals] = useState<VisualEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiClient.listVisuals({
        tenantId: tenantId ?? DEFAULT_TENANT_ID,
        spaceId: spaceId ?? "all",
      });
      const raw = (res.data ?? []) as VisualEntry[];
      setVisuals(raw.map((v) => ({
        ...v,
        image_prompt: (v.config as Record<string, unknown>)?.prompt as string ?? v.image_prompt ?? v.name ?? "",
        trace_id: v.id,
      })));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load visuals");
    } finally {
      setLoading(false);
    }
  }, [tenantId, spaceId]);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <div className="space-y-6" suppressHydrationWarning>
      <div suppressHydrationWarning>
        <h1 className="text-2xl font-bold tracking-tight text-neutral-100">
          Visuals
        </h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Generated visual prompts from runs.
        </p>
      </div>
      {error && <ErrorState message={error} onRetry={load} />}
      {loading ? (
        <p className="text-sm text-neutral-400">Loading…</p>
      ) : (
        <>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {visuals.map((v, i) => (
              <VisualCard
                key={v.id ?? v.trace_id ?? i}
                image_prompt={v.image_prompt ?? ""}
                aspect_ratio={v.aspect_ratio}
                format={v.format}
                alt_text={v.alt_text}
                trace_id={v.trace_id ?? v.id}
              />
            ))}
          </div>
          {visuals.length === 0 && !error && (
            <p className="text-sm text-neutral-400">
              No visuals yet. Run the pipeline to generate visual specs.
            </p>
          )}
        </>
      )}
    </div>
  );
}
