"use client";

import React, { useState, Suspense } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { PageSkeleton } from "@/components/dashboard/PageSkeleton";
import { ErrorState } from "@/components/feedback/ErrorState";
import { apiClient } from "@/lib/apiClient";
import { DEFAULT_TENANT_ID } from "@/lib/constants";
import { useTenantContextStore } from "@/lib/stores/tenantContextStore";
import { Lightbulb } from "lucide-react";

const SUGGESTION_QUERIES = [
  "What should I focus on today?",
  "What are my top 3 priorities this week?",
  "What commitments am I at risk of missing?",
  "Suggest a balanced plan across Work, Health, and Learning for this week.",
];

function SuggestionsContent() {
  const { tenantId, spaceId } = useTenantContextStore();
  const [query, setQuery] = useState(SUGGESTION_QUERIES[0]);
  const [answer, setAnswer] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleAsk() {
    if (!query.trim()) return;
    setLoading(true);
    setError(null);
    setAnswer(null);
    try {
      const res = await apiClient.askV1({
        tenant_id: DEFAULT_TENANT_ID,
        space_id: spaceId ?? "all",
        query: query.trim(),
      });
      setAnswer(res.answer);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ask failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-6" suppressHydrationWarning>
      <div suppressHydrationWarning>
        <h1 className="text-2xl font-bold tracking-tight text-textMain flex items-center gap-2">
          <Lightbulb className="h-7 w-7 text-primary" />
          Suggestions
        </h1>
        <p className="mt-1 text-sm text-textSoft">
          Ask your Second Brain for priorities, weekly review, or balanced plans.
        </p>
      </div>

      <Card className="rounded-2xl border border-[color:var(--color-border-subtle)] bg-surface1/90 shadow-soft">
        <CardHeader>
          <CardTitle className="text-base text-textMain">Weekly review & suggestions</CardTitle>
          <p className="text-xs text-textSoft mt-0.5">Pick a question or type your own.</p>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap gap-2">
            {SUGGESTION_QUERIES.map((q) => (
              <button
                key={q}
                type="button"
                onClick={() => setQuery(q)}
                className={`rounded-full border px-3 py-2 text-xs transition-colors ${
                  query === q
                    ? "border-primary bg-primary/15 text-primary"
                    : "border-[color:var(--color-border-subtle)] bg-surface2 text-textMain hover:bg-surface3"
                }`}
              >
                {q}
              </button>
            ))}
          </div>
          <div className="flex flex-wrap items-end gap-2">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleAsk()}
              placeholder="Or type your own question…"
              className="min-w-[200px] flex-1 rounded-xl border border-[color:var(--color-border-subtle)] bg-surface2 px-3 py-2 text-sm text-textMain placeholder:text-textSoft focus:outline-none focus:ring-2 focus:ring-primary"
            />
            <button
              type="button"
              onClick={() => handleAsk()}
              disabled={loading || !query.trim()}
              className="rounded-xl border border-primary bg-primary px-4 py-2 text-sm font-medium text-bg hover:opacity-90 disabled:opacity-50"
            >
              {loading ? "Thinking…" : "Ask"}
            </button>
          </div>
          {error && <ErrorState message={error} onRetry={handleAsk} />}
          {answer && (
            <div className="rounded-xl border border-[color:var(--color-border-subtle)] bg-surface2/80 p-4 text-sm text-textMain">
              <p className="whitespace-pre-wrap">{answer}</p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

export default function SuggestionsPage() {
  return (
    <Suspense fallback={<PageSkeleton title subtitle />}>
      <SuggestionsContent />
    </Suspense>
  );
}
