"use client";

import React, { useCallback, useEffect, useState } from "react";
import {
  apiClient,
  type M3Kpis,
  type M3Reflection,
  type M3ReflectionSearchHit,
  type M3ReflectionsResponse,
} from "@/lib/apiClient";
import { PageSkeleton } from "@/components/dashboard/PageSkeleton";
import { ErrorState } from "@/components/feedback/ErrorState";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Target, RefreshCw, Send, BarChart3, Calendar, CalendarDays, Search } from "lucide-react";

export default function M3Page() {
  const [reflections, setReflections] = useState<M3Reflection[]>([]);
  const [kpis, setKpis] = useState<M3Kpis | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reflectionText, setReflectionText] = useState("");
  const [mood, setMood] = useState("");
  const [submitLoading, setSubmitLoading] = useState(false);
  const [submitSuccess, setSubmitSuccess] = useState<string | null>(null);
  const [synthesisLoading, setSynthesisLoading] = useState(false);
  const [evolutionLoading, setEvolutionLoading] = useState(false);
  const [triggerSuccess, setTriggerSuccess] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchLoading, setSearchLoading] = useState(false);
  const [reflectionsMeta, setReflectionsMeta] = useState<M3ReflectionsResponse["meta"] | null>(null);

  const load = useCallback(async (opts?: { q?: string }) => {
    setLoading(true);
    setError(null);
    try {
      const [refRes, kpisRes] = await Promise.all([
        apiClient.m3ListReflections({ limit: 20, q: opts?.q }),
        opts?.q ? Promise.resolve(null as M3Kpis | null) : apiClient.m3GetKpis({ days: 7 }),
      ]);
      setReflections(refRes.data ?? []);
      setReflectionsMeta(refRes.meta ?? null);
      if (!opts?.q) setKpis(kpisRes ?? null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load M3 data");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!reflectionText.trim()) return;
    setSubmitLoading(true);
    setSubmitSuccess(null);
    try {
      await apiClient.m3Reflect({
        reflection_text: reflectionText.trim(),
        mood: mood.trim() || undefined,
      });
      setReflectionText("");
      setMood("");
      setSubmitSuccess("Reflection submitted.");
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Submit failed");
    } finally {
      setSubmitLoading(false);
    }
  }

  async function handleSynthesis() {
    setSynthesisLoading(true);
    setTriggerSuccess(null);
    try {
      await apiClient.m3SynthesisRequest({});
      setTriggerSuccess("Weekly synthesis requested.");
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Synthesis request failed");
    } finally {
      setSynthesisLoading(false);
    }
  }

  async function handleEvolution() {
    setEvolutionLoading(true);
    setTriggerSuccess(null);
    try {
      await apiClient.m3EvolutionRequest({});
      setTriggerSuccess("Monthly evolution requested.");
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Evolution request failed");
    } finally {
      setEvolutionLoading(false);
    }
  }

  async function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    const q = searchQuery.trim();
    if (!q) return;
    setSearchLoading(true);
    setError(null);
    try {
      const refRes = await apiClient.m3ListReflections({ limit: 20, q });
      setReflections(refRes.data ?? []);
      setReflectionsMeta(refRes.meta ?? null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Search failed");
    } finally {
      setSearchLoading(false);
    }
  }

  const isSearchResults = reflectionsMeta?.search === true;
  const searchHits = isSearchResults ? (reflections as M3ReflectionSearchHit[]) : [];

  if (loading && reflections.length === 0 && !kpis) {
    return <PageSkeleton title subtitle tableRows={5} />;
  }

  if (error && !reflections.length && !kpis) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-semibold flex items-center gap-2">
          <Target className="h-6 w-6" />
          M3 Identity
        </h1>
        <ErrorState message={error} onRetry={load} />
      </div>
    );
  }

  return (
    <div className="space-y-6" suppressHydrationWarning>
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold flex items-center gap-2">
          <Target className="h-6 w-4" />
          M3 Identity
        </h1>
        <Button variant="outline" size="sm" onClick={load} disabled={loading}>
          <RefreshCw className={`h-4 w-4 mr-1 ${loading ? "animate-spin" : ""}`} />
          Refresh
        </Button>
      </div>

      <form onSubmit={handleSubmit} className="space-y-3">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Daily reflection</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <textarea
              className="w-full min-h-[120px] rounded-lg border border-border bg-surface px-3 py-2 text-sm"
              placeholder="How are you? What mattered today?"
              value={reflectionText}
              onChange={(e) => setReflectionText(e.target.value)}
            />
            <input
              className="w-full max-w-xs rounded-lg border border-border bg-surface px-3 py-2 text-sm"
              placeholder="Mood (optional)"
              value={mood}
              onChange={(e) => setMood(e.target.value)}
            />
            <Button type="submit" disabled={submitLoading || !reflectionText.trim()}>
              <Send className="h-4 w-4 mr-2" />
              {submitLoading ? "Submitting…" : "Submit reflection"}
            </Button>
            {submitSuccess && (
              <p className="text-sm text-green-600 dark:text-green-400">{submitSuccess}</p>
            )}
          </CardContent>
        </Card>
      </form>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Synthesis & evolution</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-3">
          <Button
            variant="outline"
            size="sm"
            onClick={handleSynthesis}
            disabled={synthesisLoading}
          >
            <Calendar className="h-4 w-4 mr-2" />
            {synthesisLoading ? "Requesting…" : "Request weekly synthesis"}
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={handleEvolution}
            disabled={evolutionLoading}
          >
            <CalendarDays className="h-4 w-4 mr-2" />
            {evolutionLoading ? "Requesting…" : "Request monthly evolution"}
          </Button>
          {triggerSuccess && (
            <p className="text-sm text-green-600 dark:text-green-400 w-full">{triggerSuccess}</p>
          )}
        </CardContent>
      </Card>

      {kpis && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <BarChart3 className="h-4 w-4" />
              KPIs (last 7 days)
            </CardTitle>
          </CardHeader>
          <CardContent className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 text-sm">
            <div>
              <p className="text-textSoft">Reflections</p>
              <p className="font-medium">
                {kpis.data.daily_reflection_completion.total_reflections} total,{" "}
                {kpis.data.daily_reflection_completion.target_met_days} days met target
              </p>
            </div>
            <div>
              <p className="text-textSoft">Recall retention</p>
              <p className="font-medium">{kpis.data.recall_retention.rate_pct}%</p>
            </div>
            <div>
              <p className="text-textSoft">Identity profile</p>
              <p className="font-medium">
                {kpis.data.identity_alignment.has_profile ? "Active" : "None yet"}
              </p>
            </div>
            <div>
              <p className="text-textSoft">Gap closure</p>
              <p className="font-medium">
                {kpis.data.gap_closure.value != null
                  ? kpis.data.gap_closure.value.toFixed(2)
                  : "—"}
                {kpis.data.gap_closure.snapshot_count > 0 && (
                  <span className="text-textSoft ml-1">
                    ({kpis.data.gap_closure.snapshot_count} snapshots)
                  </span>
                )}
              </p>
            </div>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="text-base">
            {isSearchResults
              ? `Search: "${reflectionsMeta?.query ?? ""}"`
              : "Recent reflections"}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <form onSubmit={handleSearch} className="flex gap-2">
            <input
              className="flex-1 max-w-sm rounded-lg border border-border bg-surface px-3 py-2 text-sm"
              placeholder="Search reflections by meaning…"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
            <Button type="submit" variant="secondary" size="sm" disabled={searchLoading || !searchQuery.trim()}>
              <Search className="h-4 w-4 mr-1" />
              {searchLoading ? "Searching…" : "Search"}
            </Button>
          </form>
          {reflections.length === 0 ? (
            <p className="text-textSoft text-sm">
              {isSearchResults ? "No matching reflections." : "No reflections yet. Submit one above."}
            </p>
          ) : isSearchResults ? (
            <ul className="space-y-3">
              {searchHits.map((r, i) => (
                <li
                  key={r.event_id ?? `hit-${i}`}
                  className="border-b border-border pb-3 last:border-0 last:pb-0 text-sm"
                >
                  {r.score != null && (
                    <p className="text-textSoft text-xs">Score: {(r.score * 100).toFixed(0)}%</p>
                  )}
                  <p className="mt-1">{r.content}</p>
                </li>
              ))}
            </ul>
          ) : (
            <ul className="space-y-3">
              {(reflections as M3Reflection[]).slice(0, 10).map((r) => (
                <li
                  key={r.id}
                  className="border-b border-border pb-3 last:border-0 last:pb-0 text-sm"
                >
                  <p className="text-textSoft text-xs">{r.reflection_date}</p>
                  <p className="mt-1">{r.reflection_text}</p>
                  {r.mood && (
                    <p className="text-textSoft text-xs mt-1">Mood: {r.mood}</p>
                  )}
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
