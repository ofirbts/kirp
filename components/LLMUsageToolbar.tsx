"use client";

import { useEffect, useState } from "react";
import { apiClient, type LlmUsageResponse } from "@/lib/apiClient";
import { Sparkles, BrainCircuit, CloudLightning, AlertTriangle } from "lucide-react";

type ProviderKey = "groq" | "openai" | "anthropic" | "gemini";

function statusColor(status: unknown): string {
  if (status === "ok") return "text-emerald-300";
  if (status === "missing_key") return "text-yellow-300";
  if (status === "not_implemented") return "text-sky-300";
  return "text-red-300";
}

function formatCost(v: unknown): string {
  if (v == null) return "—";
  const n = Number(v);
  if (!Number.isFinite(n)) return "—";
  if (n === 999 || n === 999.0) return "—";
  return `$${n.toFixed(4)}`;
}

export default function LLMUsageToolbar() {
  const [usage, setUsage] = useState<LlmUsageResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    const load = async () => {
      try {
        const data = await apiClient.getLlmUsage();
        if (!cancelled) {
          setUsage(data);
          setError(null);
        }
      } catch (e) {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : "Failed to load LLM usage");
        }
      }
    };

    load();
    const id = setInterval(load, 30_000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  if (!usage && !error) return null;

  const providers: ProviderKey[] = ["groq", "openai", "anthropic", "gemini"];

  const best = usage?.recommendation ?? "";

  return (
    <div className="w-full border-b border-white/10 bg-surface1/80 backdrop-blur-md px-4 py-1.5 text-xs md:text-sm flex items-center justify-between gap-3">
      <div className="flex items-center gap-2 text-textSoft">
        <BrainCircuit className="h-4 w-4 text-secondary" />
        <span className="hidden sm:inline font-semibold tracking-wide uppercase">
          LLM Routing
        </span>
        {best && (
          <span className="flex items-center gap-1 text-primary font-medium">
            <Sparkles className="h-3 w-3" />
            {best}
          </span>
        )}
        {error && (
          <span className="flex items-center gap-1 text-red-300">
            <AlertTriangle className="h-3 w-3" />
            {error}
          </span>
        )}
      </div>

      {usage && (
        <div className="flex items-center gap-4 text-[11px] md:text-xs">
          {providers.map((key) => {
            const data = (usage as any)[key] || {};
            const providerStatus = data.status as string | undefined;
            let label = "";
            if (key === "groq") label = "Groq";
            else if (key === "openai") label = "OpenAI";
            else if (key === "anthropic") label = "Anthropic";
            else if (key === "gemini") label = "Gemini";

            const cost =
              key === "groq"
                ? formatCost(data.cost_usd)
                : formatCost(
                    (data.raw && (data.raw.total_usage ?? data.raw.cost_usd)) ??
                      undefined,
                  );

            return (
              <div
                key={key}
                className="flex items-center gap-1 rounded-full bg-surface2/80 px-2.5 py-0.5 border border-white/5"
              >
                <CloudLightning className="h-3 w-3 text-secondary" />
                <span className="font-semibold">{label}</span>
                <span className={statusColor(providerStatus)}>
                  {providerStatus === "missing_key"
                    ? "no key"
                    : providerStatus === "not_implemented"
                    ? "n/a"
                    : cost}
                </span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

