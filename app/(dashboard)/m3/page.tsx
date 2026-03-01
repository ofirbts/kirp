"use client";

import React, { useCallback, useEffect, useState } from "react";
import {
  apiClient,
  type M3Kpis,
  type M3Reflection,
  type M3ReflectionSearchHit,
  type M3ReflectionsResponse,
  type M3MicroAction,
  type M3Synthesis,
  type M3Evolution,
} from "@/lib/apiClient";
import { PageSkeleton } from "@/components/dashboard/PageSkeleton";
import { ErrorState } from "@/components/feedback/ErrorState";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Target, RefreshCw, Send, BarChart3, Calendar, CalendarDays, Search, CheckSquare, ListTodo, List, Download } from "lucide-react";

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
  const [actions, setActions] = useState<M3MicroAction[]>([]);
  const [syntheses, setSyntheses] = useState<M3Synthesis[]>([]);
  const [evolutions, setEvolutions] = useState<M3Evolution[]>([]);
  const [dateSince, setDateSince] = useState<string>("");
  const [dateUntil, setDateUntil] = useState<string>("");
  const [filterPreset, setFilterPreset] = useState<"all" | "7" | "30">("all");
  const [exportLoading, setExportLoading] = useState(false);

  const load = useCallback(async (opts?: { q?: string; since?: string; until?: string }) => {
    setLoading(true);
    setError(null);
    const since = opts?.since ?? dateSince;
    const until = opts?.until ?? dateUntil;
    try {
      if (opts?.q) {
        const refRes = await apiClient.m3ListReflections({ limit: 20, q: opts.q });
        setReflections(refRes.data ?? []);
        setReflectionsMeta(refRes.meta ?? null);
      } else {
        const [refRes, kpisRes, actionsRes, synthRes, evoRes] = await Promise.all([
          apiClient.m3ListReflections({ limit: 50, since: since || undefined, until: until || undefined }),
          apiClient.m3GetKpis({ days: 7 }),
          apiClient.m3ListActions({ limit: 50 }),
          apiClient.m3ListSynthesis({ limit: 10 }),
          apiClient.m3ListEvolution({ limit: 6 }),
        ]);
        setReflections(refRes.data ?? []);
        setReflectionsMeta(refRes.meta ?? null);
        setKpis(kpisRes ?? null);
        setActions(actionsRes.data ?? []);
        setSyntheses(synthRes.data ?? []);
        setEvolutions(evoRes.data ?? []);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load M3 data");
    } finally {
      setLoading(false);
    }
  }, [dateSince, dateUntil]);

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

  async function handleBackToList() {
    setSearchQuery("");
    setReflectionsMeta(null);
    setLoading(true);
    setError(null);
    try {
      const [refRes, kpisRes, actionsRes, synthRes, evoRes] = await Promise.all([
        apiClient.m3ListReflections({ limit: 20 }),
        apiClient.m3GetKpis({ days: 7 }),
        apiClient.m3ListActions({ limit: 50 }),
        apiClient.m3ListSynthesis({ limit: 10 }),
        apiClient.m3ListEvolution({ limit: 6 }),
      ]);
      setReflections(refRes.data ?? []);
      setReflectionsMeta(refRes.meta ?? null);
      setKpis(kpisRes ?? null);
      setActions(actionsRes.data ?? []);
      setSyntheses(synthRes.data ?? []);
      setEvolutions(evoRes.data ?? []);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load");
    } finally {
      setLoading(false);
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
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={load} disabled={loading}>
            <RefreshCw className={`h-4 w-4 mr-1 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={async () => {
              setExportLoading(true);
              try {
                const data = await apiClient.m3Export({
                  since: dateSince || undefined,
                  until: dateUntil || undefined,
                });
                const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
                const url = URL.createObjectURL(blob);
                const a = document.createElement("a");
                a.href = url;
                a.download = `m3-export-${new Date().toISOString().slice(0, 10)}.json`;
                a.click();
                URL.revokeObjectURL(url);
              } catch (e) {
                setError(e instanceof Error ? e.message : "Export failed");
              } finally {
                setExportLoading(false);
              }
            }}
            disabled={exportLoading}
          >
            <Download className={`h-4 w-4 mr-1 ${exportLoading ? "animate-pulse" : ""}`} />
            Export
          </Button>
        </div>
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

      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <CheckSquare className="h-4 w-4" />
            Micro-actions
          </CardTitle>
        </CardHeader>
        <CardContent>
          {loading && !isSearchResults ? (
            <p className="text-textSoft text-sm">Loading…</p>
          ) : actions.length === 0 ? (
            <p className="text-textSoft text-sm">No micro-actions yet. They are generated from reflections.</p>
          ) : (
            <ul className="space-y-2">
              {actions.slice(0, 15).map((a) => (
                <li key={a.action_id} className="flex items-start gap-2 text-sm border-b border-border pb-2 last:border-0">
                  <span className="font-medium flex-1">{a.title}</span>
                  {a.pillar && <span className="text-textSoft text-xs shrink-0">{a.pillar}</span>}
                  <span
                    className={`shrink-0 text-xs px-1.5 py-0.5 rounded ${
                      a.status === "completed"
                        ? "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300"
                        : a.status === "snoozed"
                          ? "bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300"
                          : "bg-muted text-muted-foreground"
                    }`}
                  >
                    {a.status}
                  </span>
                  {a.due_by && <span className="text-textSoft text-xs shrink-0">{a.due_by.slice(0, 10)}</span>}
                </li>
              ))}
            </ul>
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
          <CardTitle className="text-base flex items-center gap-2">
            <ListTodo className="h-4 w-4" />
            Recent syntheses & evolution
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {loading && !isSearchResults ? (
            <p className="text-textSoft text-sm">Loading…</p>
          ) : (
            <>
              {syntheses.length > 0 && (
                <div>
                  <p className="text-textSoft text-xs font-medium mb-2">Weekly syntheses</p>
                  <ul className="space-y-2">
                    {syntheses.slice(0, 5).map((s) => (
                      <li key={s.synthesis_id} className="text-sm border-b border-border pb-2 last:border-0">
                        <p className="text-textSoft text-xs">{s.week_start} – {s.week_end}</p>
                        <p className="mt-0.5">{s.summary ? (s.summary.slice(0, 120) + (s.summary.length > 120 ? "…" : "")) : "—"}</p>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              {evolutions.length > 0 && (
                <div>
                  <p className="text-textSoft text-xs font-medium mb-2">Monthly evolutions</p>
                  <ul className="space-y-2">
                    {evolutions.slice(0, 5).map((e) => (
                      <li key={e.evolution_id} className="text-sm border-b border-border pb-2 last:border-0">
                        <p className="text-textSoft text-xs">{e.month}</p>
                        <p className="mt-0.5">
                          {e.new_goals?.length ? e.new_goals.slice(0, 2).join("; ") : (Array.isArray(e.trajectory) && e.trajectory[0])
                            ? String((e.trajectory[0] as { summary?: string }).summary ?? e.trajectory[0]).slice(0, 80) + "…"
                            : "—"}
                        </p>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              {syntheses.length === 0 && evolutions.length === 0 && (
                <p className="text-textSoft text-sm">No syntheses or evolutions yet. Use the buttons above to request them.</p>
              )}
            </>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">
            {isSearchResults
              ? `Search: "${reflectionsMeta?.query ?? ""}"`
              : "Recent reflections"}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <form onSubmit={handleSearch} className="flex flex-wrap gap-2 items-center">
            <input
              className="flex-1 min-w-[200px] rounded-lg border border-border bg-surface px-3 py-2 text-sm"
              placeholder="Search reflections by meaning…"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
            <Button type="submit" variant="secondary" size="sm" disabled={searchLoading || !searchQuery.trim()}>
              <Search className="h-4 w-4 mr-1" />
              {searchLoading ? "Searching…" : "Search"}
            </Button>
            {isSearchResults && (
              <Button type="button" variant="ghost" size="sm" onClick={handleBackToList} disabled={loading}>
                <List className="h-4 w-4 mr-1" />
                Back to list
              </Button>
            )}
          </form>
          {searchLoading && (
            <p className="text-textSoft text-sm">Searching…</p>
          )}
          {!isSearchResults && (
            <div className="flex flex-wrap gap-2 items-center">
              <span className="text-textSoft text-xs">Date range:</span>
              <Button
                type="button"
                variant={filterPreset === "all" ? "secondary" : "ghost"}
                size="sm"
                onClick={() => {
                  setFilterPreset("all");
                  setDateSince("");
                  setDateUntil("");
                  load({ since: "", until: "" });
                }}
              >
                All
              </Button>
              <Button
                type="button"
                variant={filterPreset === "7" ? "secondary" : "ghost"}
                size="sm"
                onClick={() => {
                  setFilterPreset("7");
                  const today = new Date();
                  const until = today.toISOString().slice(0, 10);
                  const since = new Date(today);
                  since.setDate(since.getDate() - 7);
                  const sinceStr = since.toISOString().slice(0, 10);
                  setDateSince(sinceStr);
                  setDateUntil(until);
                  load({ since: sinceStr, until });
                }}
              >
                Last 7 days
              </Button>
              <Button
                type="button"
                variant={filterPreset === "30" ? "secondary" : "ghost"}
                size="sm"
                onClick={() => {
                  setFilterPreset("30");
                  const today = new Date();
                  const until = today.toISOString().slice(0, 10);
                  const since = new Date(today);
                  since.setDate(since.getDate() - 30);
                  const sinceStr = since.toISOString().slice(0, 10);
                  setDateSince(sinceStr);
                  setDateUntil(until);
                  load({ since: sinceStr, until });
                }}
              >
                Last 30 days
              </Button>
              {(dateSince || dateUntil) && (
                <span className="text-textSoft text-xs">
                  {dateSince || "…"} – {dateUntil || "…"}
                </span>
              )}
            </div>
          )}
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
                  {(r.mood || (r.pillar_scores && Object.keys(r.pillar_scores).length > 0)) && (
                    <div className="text-textSoft text-xs mt-1 flex flex-wrap gap-x-3 gap-y-0.5">
                      {r.mood && <span>Mood: {r.mood}</span>}
                      {r.pillar_scores && Object.keys(r.pillar_scores).length > 0 && (
                        <span>
                          Pillars:{" "}
                          {Object.entries(r.pillar_scores)
                            .map(([k, v]) => `${k} ${typeof v === "number" ? (v * 100).toFixed(0) + "%" : v}`)
                            .join(", ")}
                        </span>
                      )}
                    </div>
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
