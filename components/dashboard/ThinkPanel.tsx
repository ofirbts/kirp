"use client";

import React, { useState } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Sparkles, ArrowRight, BrainCircuit, Globe, Database } from "lucide-react";
import { cn } from "@/lib/utils";
import { apiClient } from "@/lib/apiClient";
import { DEFAULT_TENANT_ID } from "@/lib/constants";
import { useTenantContextStore } from "@/lib/stores/tenantContextStore";

type ThinkResult = {
  answer: string;
  sources: any[];
  agents_used: string[];
  needs_external_info: boolean;
};

export const ThinkPanel = () => {
  const { tenantId, spaceId } = useTenantContextStore();
  const [query, setQuery] = useState("");
  const [isThinking, setIsThinking] = useState(false);
  const [result, setResult] = useState<ThinkResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleThink = async () => {
    if (!query.trim()) return;
    setIsThinking(true);
    setResult(null);
    setError(null);

    try {
      // For now we call /api/v1/ask and wrap the response into the ThinkResult shape.
      const res = await apiClient.askV1({
        tenant_id: tenantId ?? DEFAULT_TENANT_ID,
        space_id: spaceId ?? "all",
        query: query.trim(),
      });

      const wrapped: ThinkResult = {
        answer: res.answer,
        sources: res.sources,
        agents_used: ["InsightAgent"],
        needs_external_info: res.needs_external_info,
      };
      setResult(wrapped);
    } catch (e) {
      setError(
        e instanceof Error
          ? e.message
          : "Think request failed. Check that the API is reachable.",
      );
    } finally {
      setIsThinking(false);
    }
  };

  return (
    <div className="w-full max-w-4xl mx-auto space-y-6">
      {/* שדה הקלט המרכזי */}
      <Card className={cn(
        "p-2 rounded-full border-2 transition-all duration-500",
        isThinking ? "border-secondary shadow-[0_0_20px_rgba(208,191,255,0.3)]" : "border-transparent"
      )}>
        <div className="flex items-center gap-3 px-4">
          <BrainCircuit className={cn(
            "h-6 w-6 transition-colors",
            isThinking ? "text-secondary animate-pulse" : "text-textSoft"
          )} />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Ask anything about your life, work or habits..."
            className="flex-1 bg-transparent border-none outline-none text-lg py-4 text-textMain placeholder:text-textSoft font-medium"
            onKeyDown={(e) => e.key === "Enter" && handleThink()}
          />
          <Button 
            onClick={handleThink}
            disabled={isThinking || !query}
            size="sm"
            className="rounded-full h-12 w-12 p-0 flex items-center justify-center transition-transform active:scale-90"
          >
            {isThinking ? (
              <div className="h-5 w-5 border-2 border-bg border-t-transparent rounded-full animate-spin" />
            ) : (
              <ArrowRight className="h-5 w-5" />
            )}
          </Button>
        </div>
      </Card>

      {/* Error state */}
      {error && !isThinking && (
        <Card className="p-4 text-sm text-red-300 bg-surface2/40 border-red-400/30">
          {error}
        </Card>
      )}

      {/* תצוגת התוצאה */}
      {result && !isThinking && !error && (
        <Card className="p-8 animate-in fade-in slide-in-from-bottom-4 duration-500 bg-surface2/30 backdrop-blur-md">
          <div className="flex items-start gap-4">
            <div className="bg-primary/20 p-2 rounded-xl">
              <Sparkles className="h-6 w-6 text-primary" />
            </div>
            <div className="space-y-6 flex-1">
              <div>
                <h4 className="text-sm font-bold text-textSoft uppercase tracking-widest mb-2">
                  KIRP Insight
                </h4>
                <p className="text-xl leading-relaxed text-textMain font-medium">
                  {result.answer}
                </p>
                {result.needs_external_info && (
                  <p className="mt-2 text-xs text-textMuted">
                    This answer is based only on your current KIRP data and may benefit
                    from external information.
                  </p>
                )}
              </div>

              {/* Agents & Sources */}
              <div className="flex flex-wrap gap-3">
                {result.agents_used.map((agent: string) => (
                  <div
                    key={agent}
                    className="flex items-center gap-2 bg-secondary/10 text-secondary px-3 py-1 rounded-full text-xs font-bold border border-secondary/20"
                  >
                    <Database className="h-3 w-3" />
                    {agent}
                  </div>
                ))}
                {result.sources.map((source: any, idx: number) => (
                  <div
                    key={idx}
                    className="flex items-center gap-2 bg-surface3 text-textMuted px-3 py-1 rounded-full text-xs font-medium border border-white/5"
                  >
                    <Globe className="h-3 w-3" />
                    {typeof source === "string" ? source : source.source ?? "Source"}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </Card>
      )}
    </div>
  );
};

