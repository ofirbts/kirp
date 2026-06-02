"use client";

import React, { useCallback, useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
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
import {
  Target,
  RefreshCw,
  Send,
  BarChart3,
  Calendar,
  CalendarDays,
  Search,
  CheckSquare,
  ListTodo,
  List,
  Download,
  Smile,
  Sparkles,
  ChevronRight,
  UserCheck,
} from "lucide-react";

type M3ReflectionRow = M3Reflection | M3ReflectionSearchHit;

// Horizontal Calendar Strip dates helper
const getCalendarDates = () => {
  const dates = [];
  const today = new Date();
  for (let i = 6; i >= 0; i--) {
    const d = new Date(today);
    d.setDate(today.getDate() - i);
    dates.push({
      dateStr: d.toISOString().slice(0, 10),
      dayName: d.toLocaleDateString("en-US", { weekday: "short" }),
      dayNum: d.getDate(),
      isToday: i === 0,
    });
  }
  return dates;
};

// Circular Progress SVG Ring
function CircularProgress({ value, label, colorClass = "text-primary" }: { value: number; label: string; colorClass?: string }) {
  const radius = 36;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (value / 100) * circumference;

  return (
    <div className="flex flex-col items-center justify-center p-3 glass-card rounded-2xl w-28 h-28 relative">
      <svg className="w-20 h-20 transform -rotate-90">
        <circle
          cx="40"
          cy="40"
          r={radius}
          className="stroke-current text-white/5"
          strokeWidth="6"
          fill="transparent"
        />
        <motion.circle
          cx="40"
          cy="40"
          r={radius}
          className={`stroke-current ${colorClass}`}
          strokeWidth="6"
          fill="transparent"
          initial={{ strokeDashoffset: circumference }}
          animate={{ strokeDashoffset }}
          transition={{ duration: 1.2, ease: "easeOut" }}
          strokeDasharray={circumference}
        />
      </svg>
      <div className="absolute top-7 text-center">
        <span className="text-sm font-bold block">{value}%</span>
        <span className="text-[10px] text-textMuted block">{label}</span>
      </div>
    </div>
  );
}

// Stagger variants for layout entry
const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.08,
    },
  },
};

const itemVariants = {
  hidden: { opacity: 0, y: 15 },
  visible: {
    opacity: 1,
    y: 0,
    transition: {
      type: "spring" as const,
      stiffness: 100,
      damping: 15,
    },
  },
};

export default function M3Page() {
  const [reflections, setReflections] = useState<M3ReflectionRow[]>([]);
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

  const calendarDates = getCalendarDates();

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
      setSubmitSuccess("Reflection submitted successfully.");
      await load();
      setTimeout(() => setSubmitSuccess(null), 4000);
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
      setTimeout(() => setTriggerSuccess(null), 4000);
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
      setTimeout(() => setTriggerSuccess(null), 4000);
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
  const searchHits: M3ReflectionSearchHit[] = isSearchResults ? (reflections as M3ReflectionSearchHit[]) : [];

  if (loading && reflections.length === 0 && !kpis) {
    return <PageSkeleton title subtitle tableRows={5} />;
  }

  if (error && !reflections.length && !kpis) {
    return (
      <div className="space-y-6">
        <h1 className="text-3xl font-extrabold tracking-tight flex items-center gap-3">
          <Target className="h-8 w-8 text-accent animate-pulse" />
          M3 Identity OS
        </h1>
        <ErrorState message={error} onRetry={load} />
      </div>
    );
  }

  // Predefined mood options
  const moodOptions = [
    { value: "Calm", emoji: "😌", color: "border-primary/40 bg-primary/10 text-primary" },
    { value: "Energized", emoji: "⚡", color: "border-accent/40 bg-accent/10 text-accent" },
    { value: "Focused", emoji: "🎯", color: "border-secondary/40 bg-secondary/10 text-secondary" },
    { value: "Tired", emoji: "😴", color: "border-coral/40 bg-coral/10 text-coral" },
    { value: "Stressed", emoji: "🤯", color: "border-coral/60 bg-coral/20 text-coral" },
  ];

  return (
    <motion.div
      className="space-y-8 max-w-7xl mx-auto"
      variants={containerVariants}
      initial="hidden"
      animate="visible"
      suppressHydrationWarning
    >
      {/* Header Panel */}
      <motion.div className="flex flex-col md:flex-row md:items-center justify-between gap-4" variants={itemVariants}>
        <div>
          <h1 className="text-3xl font-extrabold tracking-tight flex items-center gap-3 text-textMain">
            <Target className="h-8 w-8 text-accent" />
            M3 Identity OS
          </h1>
          <p className="text-textMuted text-sm mt-1">Controlled reflection, tracking, and identity evolution.</p>
        </div>
        <div className="flex gap-3">
          <Button
            variant="outline"
            size="sm"
            onClick={load}
            disabled={loading}
            className="rounded-xl border-border bg-surface1 backdrop-blur-md transition-all duration-300 hover:scale-105 hover:bg-surface2"
          >
            <RefreshCw className={`h-4 w-4 mr-2 ${loading ? "animate-spin" : ""}`} />
            Refresh Stack
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
            className="rounded-xl border-border bg-surface1 backdrop-blur-md transition-all duration-300 hover:scale-105 hover:bg-surface2 text-textMain"
          >
            <Download className={`h-4 w-4 mr-2 ${exportLoading ? "animate-pulse" : ""}`} />
            Export Data
          </Button>
        </div>
      </motion.div>

      {/* Calendar Strip & KPI Rings */}
      <motion.div className="grid grid-cols-1 lg:grid-cols-3 gap-6" variants={itemVariants}>
        {/* Calendar Strip Card */}
        <div className="lg:col-span-2 glass-card rounded-3xl p-6 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4">
              <span className="text-sm font-bold text-textMain flex items-center gap-2">
                <CalendarDays className="h-4 w-4 text-primary" />
                Reflections Timeline
              </span>
              <span className="text-xs text-textMuted">Last 7 days</span>
            </div>
            <div className="flex justify-between items-center gap-2 overflow-x-auto pb-2">
              {calendarDates.map((d, index) => (
                <motion.div
                  key={index}
                  className={`flex flex-col items-center p-3 rounded-2xl border min-w-[64px] transition-all ${
                    d.isToday
                      ? "border-accent/40 bg-accent/15 text-accent shadow-lg shadow-accent/10"
                      : "border-border bg-white/5 text-textMain"
                  }`}
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                >
                  <span className="text-[10px] uppercase font-bold text-textMuted">{d.dayName}</span>
                  <span className="text-lg font-extrabold mt-1">{d.dayNum}</span>
                  {d.isToday && (
                    <span className="w-1.5 h-1.5 rounded-full bg-accent mt-1.5 animate-pulse" />
                  )}
                </motion.div>
              ))}
            </div>
          </div>
          <div className="text-xs text-textMuted border-t border-border/40 pt-3 mt-4 flex items-center gap-2">
            <Sparkles className="h-3 w-3 text-secondary animate-pulse" />
            Consistency fosters cognitive alignment. Reflect daily to track vectors.
          </div>
        </div>

        {/* Circular KPI Indicators */}
        <div className="glass-card rounded-3xl p-6 flex items-center justify-around gap-4">
          <CircularProgress
            value={kpis ? Math.round(kpis.data.recall_retention.rate_pct) : 0}
            label="Recall Rate"
            colorClass="text-primary"
          />
          <CircularProgress
            value={kpis ? Math.round((kpis.data.daily_reflection_completion.target_met_days / 7) * 100) : 0}
            label="Completion"
            colorClass="text-secondary"
          />
        </div>
      </motion.div>

      {/* Main Grid: Reflection Input & Synthesis controls */}
      <motion.div className="grid grid-cols-1 lg:grid-cols-3 gap-6" variants={itemVariants}>
        {/* Daily Reflection Input Form */}
        <div className="lg:col-span-2 glass-card rounded-3xl p-6">
          <div className="flex items-center gap-2 mb-4 border-b border-border/40 pb-3">
            <Smile className="h-5 w-5 text-accent" />
            <span className="font-extrabold tracking-tight text-textMain">Submit Daily Reflection</span>
          </div>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="relative">
              <textarea
                className="w-full min-h-[140px] rounded-2xl border border-border bg-white/5 focus:bg-white/10 px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-accent/40 placeholder-textSoft text-textMain transition-all"
                placeholder="What mattered today? Note alignment, challenges, or insights..."
                value={reflectionText}
                onChange={(e) => setReflectionText(e.target.value)}
              />
            </div>

            {/* Mood Picker */}
            <div className="space-y-2">
              <label className="text-xs font-bold text-textMuted">Current Mood State</label>
              <div className="flex flex-wrap gap-2">
                {moodOptions.map((opt) => (
                  <motion.button
                    key={opt.value}
                    type="button"
                    onClick={() => setMood(mood === opt.value ? "" : opt.value)}
                    className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl border text-xs font-medium transition-all ${
                      mood === opt.value
                        ? `${opt.color} border-current ring-1 ring-current`
                        : "border-border bg-white/5 hover:bg-white/10 text-textMuted hover:text-textMain"
                    }`}
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                  >
                    <span>{opt.emoji}</span>
                    <span>{opt.value}</span>
                  </motion.button>
                ))}
              </div>
            </div>

            <div className="flex items-center justify-between pt-2">
              <Button
                type="submit"
                disabled={submitLoading || !reflectionText.trim()}
                className="rounded-xl px-5 bg-accent text-accent-foreground font-semibold shadow-lg shadow-accent/25 hover:shadow-accent/40 transition-all duration-300 hover:scale-102"
              >
                <Send className="h-4 w-4 mr-2" />
                {submitLoading ? "Analyzing Reflection..." : "Commit Reflection"}
              </Button>
              <AnimatePresence>
                {submitSuccess && (
                  <motion.span
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0 }}
                    className="text-xs text-primary font-bold flex items-center gap-1.5"
                  >
                    <Sparkles className="h-3 w-3 animate-bounce" />
                    {submitSuccess}
                  </motion.span>
                )}
              </AnimatePresence>
            </div>
          </form>
        </div>

        {/* Synthesis & Evolution Commands */}
        <div className="glass-card rounded-3xl p-6 flex flex-col justify-between">
          <div>
            <div className="flex items-center gap-2 mb-4 border-b border-border/40 pb-3">
              <Sparkles className="h-5 w-5 text-secondary animate-pulse" />
              <span className="font-extrabold tracking-tight text-textMain">Identity Evolution</span>
            </div>
            <p className="text-xs text-textMuted mb-5 leading-relaxed">
              Compile daily reflections into weekly summaries or monthly vector updates to review long-term progression.
            </p>
            <div className="space-y-3">
              <Button
                variant="outline"
                onClick={handleSynthesis}
                disabled={synthesisLoading}
                className="w-full justify-start rounded-xl py-5 border-border bg-white/5 hover:bg-white/10 text-textMain transition-all hover:translate-x-1"
              >
                <Calendar className="h-4 w-4 mr-3 text-primary" />
                <div className="text-left">
                  <span className="block text-xs font-bold">{synthesisLoading ? "Processing..." : "Weekly Synthesis"}</span>
                  <span className="block text-[10px] text-textMuted font-normal">Generate summaries & insights</span>
                </div>
              </Button>
              <Button
                variant="outline"
                onClick={handleEvolution}
                disabled={evolutionLoading}
                className="w-full justify-start rounded-xl py-5 border-border bg-white/5 hover:bg-white/10 text-textMain transition-all hover:translate-x-1"
              >
                <CalendarDays className="h-4 w-4 mr-3 text-secondary" />
                <div className="text-left">
                  <span className="block text-xs font-bold">{evolutionLoading ? "Evolving..." : "Monthly Evolution"}</span>
                  <span className="block text-[10px] text-textMuted font-normal">Recalculate alignment vectors</span>
                </div>
              </Button>
            </div>
          </div>

          <AnimatePresence>
            {triggerSuccess && (
              <motion.div
                initial={{ opacity: 0, y: 5 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                className="mt-4 p-3 rounded-2xl bg-white/5 border border-primary/20 text-xs text-primary font-bold text-center flex items-center justify-center gap-2"
              >
                <UserCheck className="h-4 w-4 animate-bounce" />
                {triggerSuccess}
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </motion.div>

      {/* Grid: Micro-actions & Syntheses timeline */}
      <motion.div className="grid grid-cols-1 lg:grid-cols-3 gap-6" variants={itemVariants}>
        {/* Micro-actions Card */}
        <div className="glass-card rounded-3xl p-6">
          <div className="flex items-center gap-2 mb-4 border-b border-border/40 pb-3">
            <CheckSquare className="h-5 w-5 text-primary" />
            <span className="font-extrabold tracking-tight text-textMain">Active Micro-actions</span>
          </div>
          <div className="max-h-[360px] overflow-y-auto pr-1 space-y-3">
            {loading && !isSearchResults ? (
              <p className="text-textSoft text-xs">Loading...</p>
            ) : actions.length === 0 ? (
              <p className="text-textSoft text-xs py-4 text-center">No micro-actions active. Committing reflections generates tasks.</p>
            ) : (
              actions.slice(0, 10).map((a) => (
                <motion.div
                  key={a.action_id}
                  className="p-3 rounded-2xl border border-border bg-white/5 hover:bg-white/10 transition-all flex flex-col gap-2 relative overflow-hidden"
                  whileHover={{ x: 2 }}
                >
                  <div className="flex items-start justify-between gap-2">
                    <span className="text-xs font-bold text-textMain leading-snug">{a.title}</span>
                    <span
                      className={`text-[9px] font-extrabold uppercase px-1.5 py-0.5 rounded-full shrink-0 ${
                        a.status === "completed"
                          ? "bg-primary/10 text-primary border border-primary/20"
                          : a.status === "snoozed"
                            ? "bg-accent/10 text-accent border border-accent/20"
                            : "bg-secondary/10 text-secondary border border-secondary/20"
                      }`}
                    >
                      {a.status}
                    </span>
                  </div>
                  <div className="flex items-center justify-between text-[10px] text-textMuted">
                    {a.pillar && (
                      <span className="px-2 py-0.5 rounded-md bg-white/5 font-medium border border-border/40">
                        {a.pillar}
                      </span>
                    )}
                    {a.due_by && <span>Due: {a.due_by.slice(0, 10)}</span>}
                  </div>
                </motion.div>
              ))
            )}
          </div>
        </div>

        {/* Syntheses & Evolution timeline */}
        <div className="lg:col-span-2 glass-card rounded-3xl p-6">
          <div className="flex items-center gap-2 mb-4 border-b border-border/40 pb-3">
            <ListTodo className="h-5 w-5 text-secondary" />
            <span className="font-extrabold tracking-tight text-textMain">Syntheses & Evolution Reports</span>
          </div>
          <div className="max-h-[360px] overflow-y-auto space-y-5 pr-1">
            {loading && !isSearchResults ? (
              <p className="text-textSoft text-xs">Loading...</p>
            ) : (
              <>
                {syntheses.length > 0 && (
                  <div className="space-y-3">
                    <span className="text-xs font-bold uppercase tracking-wider text-textMuted block">Weekly Syntheses</span>
                    <div className="space-y-3">
                      {syntheses.slice(0, 3).map((s) => (
                        <div key={s.synthesis_id} className="p-4 rounded-2xl border border-border bg-white/5 hover:bg-white/10 transition-all">
                          <div className="flex items-center justify-between mb-2">
                            <span className="text-[10px] font-bold text-primary">{s.week_start} – {s.week_end}</span>
                            <span className="text-[10px] text-textMuted">Weekly Summary</span>
                          </div>
                          <p className="text-xs text-textMain leading-relaxed">
                            {s.summary ? s.summary : "No summary content."}
                          </p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                {evolutions.length > 0 && (
                  <div className="space-y-3 pt-2">
                    <span className="text-xs font-bold uppercase tracking-wider text-textMuted block">Monthly Evolutions</span>
                    <div className="space-y-3">
                      {evolutions.slice(0, 2).map((e) => (
                        <div key={e.evolution_id} className="p-4 rounded-2xl border border-border bg-white/5 hover:bg-white/10 transition-all">
                          <div className="flex items-center justify-between mb-2">
                            <span className="text-[10px] font-bold text-secondary">{e.month}</span>
                            <span className="text-[10px] text-textMuted">Vector shift report</span>
                          </div>
                          <p className="text-xs text-textMain leading-relaxed font-semibold">
                            Goals: {e.new_goals?.length ? e.new_goals.join("; ") : "No new goals logged."}
                          </p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                {syntheses.length === 0 && evolutions.length === 0 && (
                  <p className="text-textSoft text-xs py-8 text-center">No reports compiled yet. Use the buttons above to generate records.</p>
                )}
              </>
            )}
          </div>
        </div>
      </motion.div>

      {/* Reflections Log & Semantic Search */}
      <motion.div className="glass-card rounded-3xl p-6" variants={itemVariants}>
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6 border-b border-border/40 pb-4">
          <div>
            <span className="font-extrabold tracking-tight text-textMain text-lg flex items-center gap-2">
              <List className="h-5 w-5 text-accent" />
              {isSearchResults ? `Semantic Matches: "${reflectionsMeta?.query}"` : "History Archive"}
            </span>
            <span className="text-xs text-textMuted block mt-0.5">Explore cognitive history by keywords or semantic meaning.</span>
          </div>

          <form onSubmit={handleSearch} className="flex gap-2 max-w-md w-full shrink-0">
            <div className="relative flex-1">
              <input
                className="w-full rounded-xl border border-border bg-white/5 focus:bg-white/10 pl-9 pr-3 py-1.5 text-xs focus:outline-none focus:ring-2 focus:ring-accent/40 placeholder-textSoft text-textMain"
                placeholder="Search reflections by concept..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
              <Search className="h-3.5 w-3.5 text-textSoft absolute left-3 top-2.5" />
            </div>
            <Button type="submit" size="sm" disabled={searchLoading || !searchQuery.trim()} className="bg-accent text-accent-foreground text-xs font-bold rounded-xl px-4">
              {searchLoading ? "..." : "Search"}
            </Button>
            {isSearchResults && (
              <Button type="button" variant="ghost" size="sm" onClick={handleBackToList} disabled={loading} className="text-xs text-textMain hover:bg-white/5 rounded-xl">
                Reset
              </Button>
            )}
          </form>
        </div>

        {/* Date presets (Hidden on search results) */}
        {!isSearchResults && (
          <div className="flex flex-wrap gap-2 items-center mb-4">
            <span className="text-textSoft text-xs font-bold">Filter Preset:</span>
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
              className="text-xs rounded-xl"
            >
              All Time
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
              className="text-xs rounded-xl"
            >
              Last 7 Days
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
              className="text-xs rounded-xl"
            >
              Last 30 Days
            </Button>
            {(dateSince || dateUntil) && (
              <span className="text-textMuted text-xs font-medium ml-2">
                Showing {dateSince || "beginning"} to {dateUntil || "today"}
              </span>
            )}
          </div>
        )}

        {/* Reflection list items */}
        <div className="space-y-4">
          {reflections.length === 0 ? (
            <p className="text-textSoft text-xs py-8 text-center">
              {isSearchResults ? "No semantic matches found for query." : "Archive is empty. Commit your first reflection."}
            </p>
          ) : isSearchResults ? (
            <div className="space-y-3">
              {searchHits.map((r, i) => (
                <motion.div
                  key={r.event_id ?? `hit-${i}`}
                  className="p-4 rounded-2xl border border-border bg-white/5 text-xs hover:bg-white/10 transition-all flex flex-col gap-1.5"
                  initial={{ opacity: 0, y: 5 }}
                  animate={{ opacity: 1, y: 0 }}
                >
                  <div className="flex items-center justify-between text-[10px] text-textMuted">
                    {r.score != null && (
                      <span className="text-primary font-bold">Match Confidence: {(r.score * 100).toFixed(0)}%</span>
                    )}
                    <span>ID: {r.event_id?.slice(0, 8)}</span>
                  </div>
                  <p className="text-textMain leading-relaxed font-medium mt-1">{r.content}</p>
                </motion.div>
              ))}
            </div>
          ) : (
            <div className="space-y-3">
              {(reflections as M3Reflection[]).slice(0, 10).map((r) => (
                <motion.div
                  key={r.id}
                  className="p-4 rounded-2xl border border-border bg-white/5 hover:bg-white/10 transition-all flex flex-col gap-2"
                  initial={{ opacity: 0, y: 5 }}
                  animate={{ opacity: 1, y: 0 }}
                  whileHover={{ scale: 1.005 }}
                >
                  <div className="flex items-center justify-between text-[10px] text-textMuted border-b border-border/40 pb-1.5">
                    <span className="font-bold">{r.reflection_date}</span>
                    <span>Ref #{r.id?.slice(0, 6)}</span>
                  </div>
                  <p className="text-xs text-textMain leading-relaxed font-medium mt-0.5">{r.reflection_text}</p>
                  {(r.mood || (r.pillar_scores && Object.keys(r.pillar_scores).length > 0)) && (
                    <div className="text-[10px] text-textMuted flex flex-wrap items-center gap-x-4 gap-y-1.5 pt-1 mt-1 border-t border-border/40">
                      {r.mood && (
                        <span className="px-2 py-0.5 rounded-md bg-white/5 border border-border/40">
                          Mood: <span className="text-textMain font-medium">{r.mood}</span>
                        </span>
                      )}
                      {r.pillar_scores && Object.keys(r.pillar_scores).length > 0 && (
                        <div className="flex items-center gap-1.5 flex-wrap">
                          <span className="text-textSoft">Pillars:</span>
                          {Object.entries(r.pillar_scores).map(([k, v]) => (
                            <span key={k} className="px-1.5 py-0.5 rounded bg-white/5 text-[9px] font-bold text-textMain">
                              {k} {typeof v === "number" ? (v * 100).toFixed(0) + "%" : v}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </motion.div>
              ))}
            </div>
          )}
        </div>
      </motion.div>
    </motion.div>
  );
}
