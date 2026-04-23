"use client";

import React, {
  Suspense,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { PageSkeleton } from "@/components/dashboard/PageSkeleton";
import { RunStatsPie } from "@/components/monitoring/RunStatsPie";
import { RunsTable } from "@/components/monitoring/RunsTable";
import { RunDetailModal } from "@/components/monitoring/RunDetailModal";
import {
  getTenantAlertsV1,
  getTenantRunsV1,
  getRunVisibilityV1,
  createTaskV1,
  type TenantRunRow,
  type TenantAlertsResponse,
  type TenantRunsResponse,
  type RunVisibilityResponse,
} from "@/lib/apiClient";
import { useTenantRunsStream } from "@/lib/hooks/useTenantRunsStream";
import { useTenantContextStore } from "@/lib/stores/tenantContextStore";
import { useAuthStore } from "@/lib/stores/authStore";
import { DEFAULT_TENANT_ID } from "@/lib/constants";
import { cn } from "@/lib/utils";
import { AlertTriangle, CheckCircle2, Radio, RefreshCw, X } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const LIMIT = 20;

const KIRP_VALUE_MEMORY_V1 = "kirp:value:v1";

type KirpValueMemoryV1 = {
  weekKey: string;
  resolvedBlockers: number;
  completedFlows: number;
  tasksCreated: number;
};

function currentWeekKey(): string {
  const d = new Date();
  const day = d.getDay();
  const mondayOffset = day === 0 ? -6 : 1 - day;
  const mon = new Date(d.getFullYear(), d.getMonth(), d.getDate() + mondayOffset);
  return `${mon.getFullYear()}-${String(mon.getMonth() + 1).padStart(2, "0")}-${String(mon.getDate()).padStart(2, "0")}`;
}

function readKirpValueMemory(): KirpValueMemoryV1 {
  const weekKey = currentWeekKey();
  if (typeof window === "undefined") {
    return { weekKey, resolvedBlockers: 0, completedFlows: 0, tasksCreated: 0 };
  }
  try {
    const raw = window.localStorage.getItem(KIRP_VALUE_MEMORY_V1);
    if (!raw) return { weekKey, resolvedBlockers: 0, completedFlows: 0, tasksCreated: 0 };
    const j = JSON.parse(raw) as KirpValueMemoryV1;
    if (j.weekKey !== weekKey) {
      return { weekKey, resolvedBlockers: 0, completedFlows: 0, tasksCreated: 0 };
    }
    return {
      weekKey,
      resolvedBlockers: Math.max(0, Math.floor(Number(j.resolvedBlockers)) || 0),
      completedFlows: Math.max(0, Math.floor(Number(j.completedFlows)) || 0),
      tasksCreated: Math.max(0, Math.floor(Number(j.tasksCreated)) || 0),
    };
  } catch {
    return { weekKey, resolvedBlockers: 0, completedFlows: 0, tasksCreated: 0 };
  }
}

function persistKirpValueMemory(m: KirpValueMemoryV1) {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(KIRP_VALUE_MEMORY_V1, JSON.stringify(m));
}

function bumpKirpValueMemory(patch: {
  resolvedBlockers?: number;
  completedFlows?: number;
  tasksCreated?: number;
}): KirpValueMemoryV1 {
  const cur = readKirpValueMemory();
  const next: KirpValueMemoryV1 = {
    weekKey: cur.weekKey,
    resolvedBlockers: cur.resolvedBlockers + (patch.resolvedBlockers ?? 0),
    completedFlows: cur.completedFlows + (patch.completedFlows ?? 0),
    tasksCreated: cur.tasksCreated + (patch.tasksCreated ?? 0),
  };
  persistKirpValueMemory(next);
  return next;
}

async function tryCreateTaskFromNextAction(
  action: NextAction,
  tenantId: string,
  userId: string | undefined,
  runs: TenantRunRow[],
): Promise<"created" | "failed" | "unavailable"> {
  const rid = action.targetRunId;
  if (!rid) return "failed";
  const row = runs.find((r) => r.run_id === rid);
  let title = action.action.trim();
  if (!title) {
    title = row
      ? `${row.workflow_type || "Run"} — ${rid.slice(0, 8)}…`
      : `Follow-up — ${rid.slice(0, 8)}…`;
  }
  if (title.length > 240) title = title.slice(0, 240);
  const description = `KIRP Next Action · run ${rid}${row?.workflow_type ? ` · ${row.workflow_type}` : ""}`;
  try {
    const res = await createTaskV1(
      { title, description, status: "open", priority: "normal" },
      { tenant_id: tenantId, user_id: userId },
    );
    if (res?.ok && res.data?.id) return "created";
    return "failed";
  } catch (e) {
    console.warn("[NextAction] createTaskV1 unavailable", e);
    return "unavailable";
  }
}

type NextActionKind = "failed" | "partial" | "processing" | "completed" | "idle";

type RunContextScrollIntent = "pending-steps" | "output";

type NextAction = {
  action: string;
  outcome: string;
  reason: string;
  confidence: string;
  impact: string;
  resultLabel: string;
  targetRunId: string | null;
  kind: NextActionKind;
};

type ExecuteNextActionResult = {
  runId: string | null;
  taskOutcome?: "created" | "failed" | "unavailable";
};

const IDLE_ACTION: NextAction = {
  action: "Start your next focused move",
  outcome: "You create momentum in your work instead of waiting for urgency.",
  reason: "You have a clear window, so one small move now compounds.",
  confidence: "Based on low-risk current context and no critical pending issues.",
  impact: "Creates forward momentum for your current priorities.",
  resultLabel: "Ready for your next step",
  targetRunId: null,
  kind: "idle",
};

function beforeAfterLabel(kind: NextActionKind): string {
  switch (kind) {
    case "failed":
      return "Blocked flow → Unblocked";
    case "partial":
      return "Incomplete → Completed";
    case "processing":
      return "Drifting → On track";
    case "completed":
      return "New output → Clear next step";
    case "idle":
    default:
      return "Idle → Started momentum";
  }
}

function riskTrustLine(kind: NextActionKind): string {
  switch (kind) {
    case "failed":
      return "Trust: Low risk · Reversible · You stay in control";
    case "partial":
      return "Trust: Safe · Finishes what already started";
    case "processing":
      return "Trust: Low risk · Keeps momentum without side effects";
    case "completed":
      return "Trust: Safe · Review only, no changes yet";
    case "idle":
    default:
      return "Trust: Low risk · Small step, easy to adjust";
  }
}

function hasMeaningfulOutput(row: TenantRunRow): boolean {
  // Heuristic only: richer workflows tend to emit more steps or model-attributed work.
  return row.steps_count >= 8 || Boolean(row.model);
}

/** Primary headline line for a run — same rules as `computeNextAction` candidates. */
function actionSentenceForRunLike(
  state: string,
  stepsCount: number,
  model: string | null,
): string | null {
  if (state === "failed") return "Fix what is blocking your progress";
  if (state === "partial") return "Finish what your work already started";
  if (state === "processing" || state === "accepted")
    return "Keep your work moving forward";
  if (state === "completed" && (stepsCount >= 8 || Boolean(model)))
    return "Review the result to unlock your next move";
  return null;
}

/** Human outcomes for the panel — derived from the same state signals as Next Action. */
function expectedImpactBullets(
  state: string,
  stepsCount: number,
  model: string | null,
): string[] {
  if (state === "failed") {
    return [
      "Unblock blocked work",
      "Clear what's in your way",
      "Get back to steady progress",
    ];
  }
  if (state === "partial") {
    return [
      "Complete the remaining steps",
      "Allow this flow to wrap up cleanly",
      "Reach a clear finished outcome",
    ];
  }
  if (state === "processing" || state === "accepted") {
    return [
      "Keep things moving forward",
      "Hold focus where it matters",
      "Avoid losing traction mid-effort",
    ];
  }
  if (state === "completed") {
    const rich = stepsCount >= 8 || Boolean(model);
    return [
      "Turn results into next actions",
      rich
        ? "Make fresh output easy to put to use"
        : "Make it easier to see what changed",
      rich
        ? "Help you decide what to do next"
        : "Lighten the mental load before your next move",
    ];
  }
  return [
    "Move your work ahead",
    "Make the next step clearer",
    "Reduce second-guessing before you continue",
  ];
}

/** Client-only signals from the runs list + recent progress memory (no visibility fetch). */
type UserContextSignals = {
  isBusy: boolean;
  hasRepetition: boolean;
  highMomentum: boolean;
  lowActivity: boolean;
  recentFailures: boolean;
};

const MS_48H = 48 * 60 * 60 * 1000;

function parseStartedAtMs(iso: string): number {
  const t = Date.parse(iso);
  return Number.isFinite(t) ? t : 0;
}

function deriveUserContextSignals(
  runs: TenantRunRow[],
  recentProgress: string[],
): UserContextSignals {
  const now = Date.now();
  const activePending = new Set(["failed", "partial", "processing", "accepted"]);
  const activeCount = runs.filter((r) => activePending.has(r.state)).length;

  const isBusy = activeCount >= 4;

  const recentFailures = runs.some(
    (r) =>
      r.state === "failed" && now - parseStartedAtMs(r.started_at) < MS_48H,
  );

  const byWorkflow = new Map<string, number>();
  const byTypeState = new Map<string, number>();
  for (const r of runs) {
    byWorkflow.set(r.workflow_type, (byWorkflow.get(r.workflow_type) ?? 0) + 1);
    const ts = `${r.workflow_type}\u0000${r.state}`;
    byTypeState.set(ts, (byTypeState.get(ts) ?? 0) + 1);
  }
  const maxWorkflow = runs.length ? Math.max(...byWorkflow.values()) : 0;
  const maxTypeState = runs.length ? Math.max(...byTypeState.values()) : 0;
  const hasRepetition = maxWorkflow >= 3 || maxTypeState >= 3;

  const highMomentum = recentProgress.length >= 2;

  const lowActivity =
    !isBusy &&
    (runs.length === 0 ||
      (activeCount <= 1 && runs.length <= 4 && !recentFailures));

  return {
    isBusy,
    hasRepetition,
    highMomentum,
    lowActivity,
    recentFailures,
  };
}

function expectedImpactBulletsEnhanced(
  state: string,
  stepsCount: number,
  model: string | null,
  signals: UserContextSignals,
): string[] {
  const b = expectedImpactBullets(state, stepsCount, model);
  let second = b[1];
  let third = b[2];

  if (signals.recentFailures) {
    second = "Restore stability to your workflow";
    third = "Prevent repeated interruptions";
  } else if (signals.isBusy) {
    second = "Reduce cognitive load";
    third = "Clear what's most blocking right now";
  } else if (signals.hasRepetition) {
    second = "Reduce repeated effort";
    third = "Turn a recurring pattern into a clean flow";
  } else if (signals.highMomentum) {
    second = "Keep your current momentum going";
    third = "Build on what you already moved forward";
  } else if (signals.lowActivity) {
    second = "Create a clear starting point";
    third = "Get your work moving again";
  }

  return [b[0], second, third];
}

function wordInText(text: string, word: string): boolean {
  return new RegExp(`\\b${word}\\b`, "i").test(text);
}

function filterImpactLinesForSilence(
  lines: string[],
  signals: UserContextSignals,
): string[] {
  return lines.filter((line) => {
    const l = line.toLowerCase();
    if (!signals.hasRepetition && (l.includes("repeat") || l.includes("recur"))) return false;
    if (!signals.recentFailures && (l.includes("stability") || l.includes("interrupt"))) return false;
    if (!signals.isBusy && l.includes("cognitive load")) return false;
    if (!signals.highMomentum && l.includes("momentum") && l.includes("going")) return false;
    if (!signals.lowActivity && l.includes("starting point")) return false;
    return true;
  });
}

function dedupeBulletsAgainstPrior(bullets: string[], prior: string): string[] {
  const keys = ["momentum", "clarity", "progress", "focus"] as const;
  const p = prior.toLowerCase();
  const out: string[] = [];
  for (const line of bullets) {
    const low = line.toLowerCase();
    let skip = false;
    for (const k of keys) {
      if (wordInText(p, k) && wordInText(low, k)) {
        skip = true;
        break;
      }
    }
    if (skip) continue;
    if (out.length > 0) {
      const prev = out[out.length - 1].toLowerCase();
      let dup = false;
      for (const k of keys) {
        if (wordInText(prev, k) && wordInText(low, k)) {
          dup = true;
          break;
        }
      }
      if (dup) continue;
    }
    out.push(line);
  }
  return out;
}

function isLineSubsumedByAnchor(line: string, anchor: string): boolean {
  const words = line.toLowerCase().match(/\b[a-z]{5,}\b/g) ?? [];
  if (words.length < 2) return false;
  const a = anchor.toLowerCase();
  const hit = words.filter((w) => a.includes(w)).length;
  return hit >= Math.ceil(words.length * 0.7);
}

function impactBulletsFinal(
  state: string,
  stepsCount: number,
  model: string | null,
  signals: UserContextSignals,
  priorWording: string,
  anchorLower: string,
  idleSoft: boolean,
): string[] {
  const raw = expectedImpactBulletsEnhanced(state, stepsCount, model, signals);
  const filtered = filterImpactLinesForSilence(raw, signals);
  const deduped = dedupeBulletsAgainstPrior(filtered, `${priorWording} ${anchorLower}`);
  const substantive = deduped.filter((l) => !isLineSubsumedByAnchor(l, anchorLower));
  let trimmed = substantive.slice(0, 2);
  if (idleSoft) trimmed = trimmed.slice(0, 1);
  return trimmed;
}

function getPersonalizationHint(signals: UserContextSignals): string {
  if (signals.recentFailures) {
    return "Given bumps in your recent activity, this is the right move.";
  }
  if (signals.isBusy) {
    return "This helps you most based on what's happening today.";
  }
  if (signals.hasRepetition) {
    return "This fits a pattern showing up often in your work lately.";
  }
  if (signals.highMomentum) {
    return "Given your recent activity, this is the right move.";
  }
  return "This fits where your work is right now.";
}

type SessionDirection = {
  theme: string;
  sentence: string;
};

function deriveSessionDirection(
  runs: TenantRunRow[],
  signals: UserContextSignals,
): SessionDirection {
  if (signals.recentFailures) {
    return {
      theme: "Stabilizing your workflow",
      sentence: "Today is about getting things back to a steady state.",
    };
  }
  if (signals.isBusy) {
    return {
      theme: "Clearing what blocks your progress",
      sentence: "Today is about making space for what matters next.",
    };
  }
  if (signals.hasRepetition) {
    return {
      theme: "Reducing repeated work",
      sentence: "This is a good moment to create clarity and direction.",
    };
  }
  if (signals.highMomentum) {
    return {
      theme: "Building on your momentum",
      sentence: "You're in a strong position to move things forward.",
    };
  }
  if (signals.lowActivity) {
    return {
      theme: "Starting fresh with focus",
      sentence: "This is a good moment to create clarity and direction.",
    };
  }
  if (runs.length >= 6) {
    return {
      theme: "Moving forward",
      sentence: "You're in a strong position to move things forward.",
    };
  }
  return {
    theme: "Moving forward",
    sentence: "This is a good moment to create clarity and direction.",
  };
}

/** Weak = little to personalize without repeating generic copy. */
function signalsAreWeak(signals: UserContextSignals): boolean {
  return (
    !signals.hasRepetition &&
    !signals.recentFailures &&
    !signals.isBusy &&
    !signals.highMomentum &&
    !signals.lowActivity
  );
}

function personalizationHintAddsMeaning(
  signals: UserContextSignals,
  direction: SessionDirection,
  hint: string,
): boolean {
  if (signalsAreWeak(signals)) return false;
  const d = `${direction.theme} ${direction.sentence}`.toLowerCase();
  const h = hint.toLowerCase();
  const keywords = [
    "momentum",
    "clarity",
    "direction",
    "focus",
    "progress",
    "pattern",
    "activity",
    "today",
    "steady",
    "forward",
  ];
  let shared = 0;
  for (const k of keywords) {
    if (wordInText(d, k) && wordInText(h, k)) shared++;
  }
  if (shared >= 2) return false;
  const h5 = h.slice(0, 28);
  const d5 = d.slice(0, 28);
  if (h5 === d5) return false;
  return true;
}

function mergeReasonAndWhyMattersOneLine(
  reason: string,
  whyMatters: string,
  kind: NextActionKind,
  signals: UserContextSignals,
): string {
  if (kind === "idle") {
    if (signals.recentFailures || signals.isBusy) return whyMatters || reason;
    return "Nothing urgent here—pick it up when a small step feels right.";
  }
  return whyMatters || reason;
}

function summarizeProgress(recentProgress: string[]): string {
  if (!recentProgress.length) return "";

  let unblock = 0;
  let completeFlow = 0;
  for (const line of recentProgress) {
    if (line.includes("Unblocked")) unblock++;
    if (line.includes("Incomplete") && line.includes("Completed")) completeFlow++;
  }

  if (unblock >= 2 && completeFlow >= 1) {
    return "You cleared 2 blockers and completed 1 flow.";
  }
  if (unblock >= 1 && completeFlow >= 1) {
    return "You cleared a blocker and wrapped a loose end.";
  }
  if (unblock >= 2) {
    return "You cleared multiple blockers in quick succession.";
  }
  if (recentProgress.length >= 2) {
    return "You've been consistently moving things forward.";
  }
  return "You started building momentum.";
}

function kindFromPanelState(state: string): NextActionKind {
  if (state === "failed") return "failed";
  if (state === "partial") return "partial";
  if (state === "processing" || state === "accepted") return "processing";
  if (state === "completed") return "completed";
  return "idle";
}

function ctaLabelForKind(kind: NextActionKind): string {
  switch (kind) {
    case "failed":
      return "Create tracked task";
    case "partial":
      return "Create tracked task";
    case "processing":
      return "Open run";
    case "completed":
      return "Open run";
    case "idle":
    default:
      return "Start something focused";
  }
}

function actionExecutionType(kind: NextActionKind): "real" | "view_only" | "guidance" {
  if (kind === "failed" || kind === "partial") return "real";
  if (kind === "processing" || kind === "completed") return "view_only";
  return "guidance";
}

/** One line under the recommendation so the click never feels ambiguous. */
function nextActionClickIntent(
  action: NextAction,
): { line: string; accentClass: string } | null {
  switch (action.kind) {
    case "failed":
    case "partial":
      if (!action.targetRunId) return null;
      return {
        line: "Creates a tracked task, then verifies this run. The panel opens only if task creation is unavailable.",
        accentClass:
          "border-l-2 border-emerald-500/45 pl-2.5 text-[11px] leading-snug text-emerald-100/85",
      };
    case "processing":
    case "completed":
      if (!action.targetRunId) return null;
      return {
        line: "Opens this run in the panel — no new task is created.",
        accentClass:
          "border-l-2 border-[color:var(--color-border-subtle)] pl-2.5 text-[11px] leading-snug text-textSoft",
      };
    case "idle":
      return {
        line: "No run is attached — this is guidance only until something needs you.",
        accentClass:
          "border-l-2 border-[color:var(--color-border-subtle)] pl-2.5 text-[11px] leading-snug text-textSoft opacity-90",
      };
    default:
      return null;
  }
}

function formatLoopContinueLine(peek: NextAction): string {
  if (peek.kind === "idle") {
    return "Next: A new recommendation will appear here when the board shifts.";
  }
  return `Next: ${peek.action}`;
}

function quietReassuranceLine(runId: string | null): string {
  const lines = [
    "This is a safe next step.",
    "You can always adjust after.",
    "Nothing here is irreversible.",
  ];
  if (!runId) return lines[0];
  let n = 0;
  for (let i = 0; i < runId.length; i++) n += runId.charCodeAt(i);
  return lines[n % 3]!;
}

const VERIFY_FETCH_TIMEOUT_MS = 8000;

async function fetchRunVisibilityOnce(
  runId: string,
  timeoutMs: number,
): Promise<RunVisibilityResponse | null> {
  const p = getRunVisibilityV1(runId).catch(() => null);
  const t = new Promise<null>((resolve) => {
    setTimeout(() => resolve(null), timeoutMs);
  });
  const out = await Promise.race([p, t]);
  return out;
}

function formatVerifiedResultLine(
  kind: NextActionKind,
  vis: RunVisibilityResponse,
): string {
  const s = (vis.state || "").toLowerCase();
  if (kind === "failed") {
    if (s === "processing" || s === "accepted") return "Unblocked — flow is now processing";
    if (s === "completed") return "Completed — output ready";
    return "Progress resumed";
  }
  if (s === "completed") return "Completed — output ready";
  if (s === "processing" || s === "accepted") return "Progress resumed";
  if (s === "partial") return "Almost there — finish the loose ends";
  if (s === "failed") return "Still needs attention — details are in the panel";
  return "Updated just now";
}

function formatProofLine(vis: RunVisibilityResponse): string {
  const done = vis.steps.filter((st) => /complete|success|ok|done/i.test(st.status));
  const last = done[done.length - 1];
  if (last) return `"${last.name}" finished`;
  return "Updated just now";
}

function getWhyThisMatters(
  signals: UserContextSignals,
  actionKind: NextActionKind,
): string {
  if (actionKind === "failed") {
    return "This will unblock the most critical part of your work right now.";
  }
  if (actionKind === "partial" || actionKind === "processing") {
    return "This keeps your current progress from slowing down.";
  }
  if (actionKind === "completed") {
    return "This turns what you already did into a real outcome.";
  }
  if (actionKind === "idle") {
    if (signals.isBusy) {
      return "This clears mental noise so your next move stays obvious.";
    }
    return "This is a good moment to create clarity and direction.";
  }
  if (signals.recentFailures) {
    return "This will unblock the most critical part of your work right now.";
  }
  if (signals.isBusy) {
    return "This clears mental noise so your next move stays obvious.";
  }
  if (signals.highMomentum) {
    return "This builds on the traction you already created.";
  }
  return "This keeps your next move obvious and light.";
}

function computeNextAction(
  runs: TenantRunRow[],
  actedRunIds: Set<string>,
): NextAction {
  if (!runs.length) return IDLE_ACTION;

  const mk = (
    row: TenantRunRow,
    kind: Exclude<NextActionKind, "idle">,
    outcome: string,
    reason: string,
    confidence: string,
    impact: string,
    resultLabel: string,
  ) => ({
    row,
    kind,
    action:
      actionSentenceForRunLike(row.state, row.steps_count, row.model) ??
      IDLE_ACTION.action,
    outcome,
    reason,
    confidence,
    impact,
    resultLabel,
  });

  const candidates = [
    ...runs
      .filter((r) => r.state === "failed")
      .map((r) =>
        mk(
          r,
          "failed",
          "You restore momentum in your work and get things moving again.",
          "Something important is stuck, and one action now reopens your flow.",
          "Based on the most recent blocked activity and unresolved errors.",
          "This will unblock pending work that cannot move without this fix.",
          "Progress unblocked",
        ),
      ),
    ...runs
      .filter((r) => r.state === "partial")
      .map((r) =>
        mk(
          r,
          "partial",
          "You turn partial progress into a completed outcome.",
          "Most of the effort is already done, so closing now gives the fastest win.",
          "Based on recent activity that advanced but did not fully close.",
          "This completes the last missing part of your current flow.",
          "Flow completed",
        ),
      ),
    ...runs
      .filter((r) => r.state === "processing" || r.state === "accepted")
      .map((r) =>
        mk(
          r,
          "processing",
          "You maintain momentum and avoid losing focus.",
          "Your active flow is already warm, so continuing now is the easiest path.",
          "Based on live in-progress activity detected in the latest timeline.",
          "This keeps your current workflow on track without extra context switching.",
          "Forward motion secured",
        ),
      ),
    ...runs
      .filter((r) => r.state === "completed" && hasMeaningfulOutput(r))
      .map((r) =>
        mk(
          r,
          "completed",
          "You turn fresh output into a confident next decision.",
          "A meaningful outcome is ready now, and quick review keeps your flow sharp.",
          "Based on a recent completed item with substantial output signals.",
          "This helps you convert new output into immediate follow-up action.",
          "Ready for next step",
        ),
      ),
  ];

  if (!candidates.length) return IDLE_ACTION;

  const MS_2H = 2 * 60 * 60 * 1000;
  const now = Date.now();
  const wfCounts = new Map<string, number>();
  for (const r of runs) {
    wfCounts.set(r.workflow_type, (wfCounts.get(r.workflow_type) ?? 0) + 1);
  }

  const scored = candidates
    .map((c, idx) => {
      let score = 0;
      if (c.kind === "failed") score += 50;
      else if (c.kind === "partial") score += 40;
      else if (c.kind === "processing") score += 30;
      else if (c.kind === "completed") score += 20;

      if (now - parseStartedAtMs(c.row.started_at) < MS_2H) score += 10;
      if ((wfCounts.get(c.row.workflow_type) ?? 0) >= 3) score += 10;

      const similarActed = [...actedRunIds].some((id) => {
        const row = runs.find((r) => r.run_id === id);
        return Boolean(row && row.workflow_type === c.row.workflow_type);
      });
      if (similarActed) score += 5;
      if (actedRunIds.has(c.row.run_id)) score -= 10;

      score -= idx * 0.001;
      return { ...c, score };
    })
    .sort((a, b) => b.score - a.score);

  const top = scored[0];
  return {
    action: top.action,
    outcome: top.outcome,
    reason: top.reason,
    confidence: top.confidence,
    impact: top.impact,
    resultLabel: top.resultLabel,
    targetRunId: top.row.run_id,
    kind: top.kind,
  };
}

function MonitoringContent() {
  const searchParams = useSearchParams();
  const urlTenant = searchParams.get("tenant")?.trim();
  const { tenantId: storeTenant } = useTenantContextStore();
  const { user, loaded } = useAuthStore();
  const skipAuth = process.env.NEXT_PUBLIC_SKIP_AUTH === "1";
  const tenantId =
    urlTenant ||
    (skipAuth
      ? storeTenant || DEFAULT_TENANT_ID
      : user?.tenant_id?.trim() || storeTenant || DEFAULT_TENANT_ID);

  const [payload, setPayload] = useState<TenantRunsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastRefresh, setLastRefresh] = useState<Date | null>(null);
  const [sseLive, setSseLive] = useState(false);
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [alertsPayload, setAlertsPayload] = useState<TenantAlertsResponse | null>(
    null,
  );
  const [actedRunIds, setActedRunIds] = useState<Set<string>>(new Set());
  const [resultState, setResultState] = useState<string | null>(null);
  const [progressFlash, setProgressFlash] = useState<string | null>(null);
  const [recentProgress, setRecentProgress] = useState<string[]>([]);
  const [resultProofLine, setResultProofLine] = useState<string | null>(null);
  const [nextActionCardCue, setNextActionCardCue] = useState<"task_created" | null>(
    null,
  );
  const [loopContinueLine, setLoopContinueLine] = useState<string | null>(null);
  const [valueMemory, setValueMemory] = useState<KirpValueMemoryV1>(() => ({
    weekKey: "",
    resolvedBlockers: 0,
    completedFlows: 0,
    tasksCreated: 0,
  }));
  const [runContextOpen, setRunContextOpen] = useState(false);
  const [runContextRunId, setRunContextRunId] = useState<string | null>(null);
  const [runContextLoading, setRunContextLoading] = useState(false);
  const [runContextError, setRunContextError] = useState<string | null>(null);
  const [runContextData, setRunContextData] = useState<RunVisibilityResponse | null>(
    null,
  );
  const runContextFetchSeq = useRef(0);
  const runContextScrollIntentRef = useRef<RunContextScrollIntent | null>(null);
  const clearNextActionFeedbackTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const lastNextActionGuardRef = useRef<{ runId: string | null; t: number }>({
    runId: null,
    t: 0,
  });

  useEffect(() => {
    setValueMemory(readKirpValueMemory());
  }, []);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [data, alerts] = await Promise.all([
        getTenantRunsV1(tenantId, { limit: LIMIT }),
        getTenantAlertsV1(tenantId).catch(() => null),
      ]);
      setPayload(data);
      setAlertsPayload(alerts);
      setLastRefresh(new Date());
    } catch (e) {
      setError(
        e instanceof Error ? e.message : "Failed to load tenant runs",
      );
      setPayload(null);
    } finally {
      setLoading(false);
    }
  }, [tenantId]);

  useEffect(() => {
    if (!skipAuth && !loaded) return;
    if (!skipAuth && !user?.tenant_id && !urlTenant) {
      setLoading(false);
      setError("No tenant in session. Try logging in again.");
      return;
    }
    void load();
  }, [load, skipAuth, loaded, user?.tenant_id, urlTenant]);

  useTenantRunsStream(tenantId, LIMIT, true, (data) => {
    setPayload(data);
    setLastRefresh(new Date());
    setSseLive(true);
  });

  useEffect(() => {
    if (!skipAuth && !loaded) return;
    if (!skipAuth && !user?.tenant_id && !urlTenant) return;
    let cancelled = false;
    const tick = () => {
      void getTenantAlertsV1(tenantId)
        .then((a) => {
          if (!cancelled) setAlertsPayload(a);
        })
        .catch(() => {});
    };
    tick();
    const id = setInterval(tick, 60000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [tenantId, skipAuth, loaded, user?.tenant_id, urlTenant]);

  useEffect(() => {
    if (!runContextOpen) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setRunContextOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [runContextOpen]);

  const closeRunContext = useCallback(() => {
    runContextScrollIntentRef.current = null;
    setRunContextOpen(false);
    setRunContextRunId(null);
    setRunContextLoading(false);
    setRunContextError(null);
    setRunContextData(null);
  }, []);

  const scheduleClearNextActionFeedback = useCallback((ms: number) => {
    if (clearNextActionFeedbackTimer.current) {
      clearTimeout(clearNextActionFeedbackTimer.current);
    }
    clearNextActionFeedbackTimer.current = setTimeout(() => {
      setResultState(null);
      setProgressFlash(null);
      setResultProofLine(null);
      setNextActionCardCue(null);
      setLoopContinueLine(null);
      clearNextActionFeedbackTimer.current = null;
    }, ms);
  }, []);

  const beginRunContextForExecution = useCallback(
    (rid: string, scrollIntent: RunContextScrollIntent | null) => {
      runContextScrollIntentRef.current = scrollIntent;
      setRunContextRunId(rid);
      setRunContextOpen(true);
      setRunContextLoading(true);
      setRunContextError(null);
      setRunContextData(null);
      const seq = ++runContextFetchSeq.current;
      void getRunVisibilityV1(rid)
        .then((data) => {
          if (seq !== runContextFetchSeq.current) return;
          setRunContextData(data);
        })
        .catch((err) => {
          if (seq !== runContextFetchSeq.current) return;
          setRunContextError(
            err instanceof Error ? err.message : "Could not load run context",
          );
        })
        .finally(() => {
          if (seq !== runContextFetchSeq.current) return;
          setRunContextLoading(false);
        });
    },
    [],
  );

  const runs = useMemo(() => payload?.runs ?? [], [payload?.runs]);

  const executeNextAction = useCallback(
    async (action: NextAction): Promise<ExecuteNextActionResult> => {
      const rid = action.targetRunId;
      switch (action.kind) {
        case "idle":
          console.log("[NextAction] start flow placeholder (idle)");
          return { runId: null };
        case "failed": {
          if (!rid) return { runId: null };
          const task = await tryCreateTaskFromNextAction(
            action,
            tenantId,
            user?.id,
            runs,
          );
          if (task === "unavailable") {
            beginRunContextForExecution(rid, null);
            return { runId: rid, taskOutcome: "unavailable" };
          }
          return { runId: rid, taskOutcome: task };
        }
        case "partial": {
          if (!rid) return { runId: null };
          const task = await tryCreateTaskFromNextAction(
            action,
            tenantId,
            user?.id,
            runs,
          );
          if (task === "unavailable") {
            beginRunContextForExecution(rid, "pending-steps");
            return { runId: rid, taskOutcome: "unavailable" };
          }
          return { runId: rid, taskOutcome: task };
        }
        case "processing": {
          if (!rid) return { runId: null };
          beginRunContextForExecution(rid, null);
          return { runId: rid };
        }
        case "completed": {
          if (!rid) return { runId: null };
          beginRunContextForExecution(rid, "output");
          return { runId: rid };
        }
        default:
          return { runId: rid };
      }
    },
    [beginRunContextForExecution, tenantId, user?.id, runs],
  );

  const verifyRunAfterAction = useCallback(async (rid: string) => {
    let vis = await fetchRunVisibilityOnce(rid, VERIFY_FETCH_TIMEOUT_MS);
    if (vis) return vis;
    setResultProofLine("Still updating…");
    setResultState("Checking latest status…");
    await new Promise((r) => setTimeout(r, 1500));
    vis = await fetchRunVisibilityOnce(rid, VERIFY_FETCH_TIMEOUT_MS);
    if (vis) return vis;
    setResultProofLine("Update in progress");
    setResultState("Update in progress");
    return null;
  }, []);

  const onRowClick = (runId: string) => {
    setSelectedRunId(runId);
    setModalOpen(true);
  };

  const stats = payload?.stats ?? {
    total: 0,
    completed: 0,
    partial: 0,
    failed: 0,
  };
  const nextAction = useMemo(
    () => computeNextAction(runs, actedRunIds),
    [runs, actedRunIds],
  );

  const peekNextAction = useMemo(() => {
    const sim = new Set(actedRunIds);
    if (nextAction.targetRunId) sim.add(nextAction.targetRunId);
    return computeNextAction(runs, sim);
  }, [runs, actedRunIds, nextAction]);

  const afterThisLine = useMemo(() => {
    const samePeek =
      nextAction.action === peekNextAction.action &&
      nextAction.kind === peekNextAction.kind &&
      nextAction.targetRunId === peekNextAction.targetRunId;
    if (samePeek) {
      return "This unlocks: The next best move will surface here when it is ready.";
    }
    return `This unlocks: ${peekNextAction.action}`;
  }, [nextAction, peekNextAction]);

  const clickIntent = useMemo(
    () => nextActionClickIntent(nextAction),
    [nextAction],
  );

  const panelRecommendedLine = useMemo(() => {
    if (!runContextRunId) return "";
    const row = runs.find((r) => r.run_id === runContextRunId);
    if (row) {
      const line = actionSentenceForRunLike(row.state, row.steps_count, row.model);
      if (line) return line;
    }
    if (runContextData) {
      const line = actionSentenceForRunLike(
        runContextData.state,
        runContextData.steps.length,
        null,
      );
      if (line) return line;
    }
    if (nextAction.targetRunId === runContextRunId) return nextAction.action;
    return "Move forward with what you reviewed.";
  }, [runContextRunId, runs, runContextData, nextAction]);

  const userContextSignals = useMemo(
    () => deriveUserContextSignals(runs, recentProgress),
    [runs, recentProgress],
  );

  const sessionDirection = useMemo(
    () => deriveSessionDirection(runs, userContextSignals),
    [runs, userContextSignals],
  );

  const weeklyMeaningfulMoves = useMemo(
    () =>
      valueMemory.tasksCreated +
      valueMemory.resolvedBlockers +
      valueMemory.completedFlows,
    [valueMemory],
  );

  const progressSummary = useMemo(
    () => summarizeProgress(recentProgress),
    [recentProgress],
  );

  const cardMergedAnchor = useMemo(() => {
    return mergeReasonAndWhyMattersOneLine(
      nextAction.reason,
      getWhyThisMatters(userContextSignals, nextAction.kind),
      nextAction.kind,
      userContextSignals,
    );
  }, [nextAction, userContextSignals]);

  const panelActionKind = useMemo((): NextActionKind => {
    if (!runContextRunId) return "idle";
    if (runContextRunId === nextAction.targetRunId) return nextAction.kind;
    const row = runs.find((r) => r.run_id === runContextRunId);
    if (row) return kindFromPanelState(row.state);
    if (runContextData) return kindFromPanelState(runContextData.state);
    return "idle";
  }, [runContextRunId, runs, runContextData, nextAction]);

  const panelMergedAnchor = useMemo(() => {
    if (!runContextRunId) return "";
    const why = getWhyThisMatters(userContextSignals, panelActionKind);
    const reason =
      runContextRunId === nextAction.targetRunId
        ? nextAction.reason
        : "Here's what stands out about this moment in your work.";
    return mergeReasonAndWhyMattersOneLine(
      reason,
      why,
      panelActionKind,
      userContextSignals,
    );
  }, [runContextRunId, nextAction, userContextSignals, panelActionKind]);

  const panelShowPersonalizationHint = useMemo(() => {
    if (!runContextOpen) return false;
    const hint = getPersonalizationHint(userContextSignals);
    return personalizationHintAddsMeaning(userContextSignals, sessionDirection, hint);
  }, [runContextOpen, userContextSignals, sessionDirection]);

  const panelIdleSoft = panelActionKind === "idle";

  const panelExpectedImpactBullets = useMemo(() => {
    if (!runContextRunId) return [];
    const signals = userContextSignals;
    const prior = `${sessionDirection.theme} ${sessionDirection.sentence}`.toLowerCase();
    const anchorLower = panelMergedAnchor.toLowerCase();
    const row = runs.find((r) => r.run_id === runContextRunId);
    if (row) {
      return impactBulletsFinal(
        row.state,
        row.steps_count,
        row.model,
        signals,
        prior,
        anchorLower,
        panelIdleSoft,
      );
    }
    if (runContextData) {
      return impactBulletsFinal(
        runContextData.state,
        runContextData.steps.length,
        null,
        signals,
        prior,
        anchorLower,
        panelIdleSoft,
      );
    }
    return impactBulletsFinal("unknown", 0, null, signals, prior, anchorLower, panelIdleSoft);
  }, [
    runContextRunId,
    runs,
    runContextData,
    userContextSignals,
    sessionDirection,
    panelMergedAnchor,
    panelIdleSoft,
  ]);

  const panelCTAQuietContext = useMemo(
    () =>
      runContextOpen &&
      !panelShowPersonalizationHint &&
      panelExpectedImpactBullets.length === 0,
    [runContextOpen, panelShowPersonalizationHint, panelExpectedImpactBullets.length],
  );

  const applyImmediateNextActionFeedback = useCallback(
    (action: NextAction) => {
      console.log("[NextAction]", action.kind, action.targetRunId, action.action);
      setResultProofLine(null);
      const ba = beforeAfterLabel(action.kind);
      setProgressFlash(ba);
      setResultState(action.resultLabel);
      const memoryLine = `${ba} — ${action.resultLabel}`;
      setRecentProgress((prev) => [memoryLine, ...prev].slice(0, 3));
      scheduleClearNextActionFeedback(4500);
    },
    [scheduleClearNextActionFeedback],
  );

  const onRunContextPanelContinue = useCallback(() => {
    closeRunContext();
    applyImmediateNextActionFeedback(nextAction);
  }, [closeRunContext, applyImmediateNextActionFeedback, nextAction]);

  useEffect(() => {
    if (!runContextData || runContextLoading) return;
    const intent = runContextScrollIntentRef.current;
    if (!intent) return;
    runContextScrollIntentRef.current = null;
    const id = requestAnimationFrame(() => {
      if (intent === "pending-steps") {
        const idx = runContextData.steps.findIndex(
          (s) => !/complete|success|ok|done|skipped/i.test(s.status),
        );
        const el = document.getElementById(
          idx >= 0 ? `run-context-step-${idx}` : "run-context-steps",
        );
        el?.scrollIntoView({ block: "nearest", behavior: "smooth" });
      } else if (intent === "output") {
        document
          .getElementById("run-context-steps-end")
          ?.scrollIntoView({ block: "end", behavior: "smooth" });
      }
    });
    return () => cancelAnimationFrame(id);
  }, [runContextData, runContextLoading]);

  const alertCount = alertsPayload?.count ?? 0;

  if (loading && !payload) {
    return <PageSkeleton title subtitle cards={2} tableRows={6} />;
  }

  const onNextActionClick = () => {
    const action = nextAction;
    const rid = action.targetRunId;
    const now = Date.now();
    if (
      rid &&
      lastNextActionGuardRef.current.runId === rid &&
      now - lastNextActionGuardRef.current.t < 1500
    ) {
      return;
    }
    lastNextActionGuardRef.current = { runId: rid, t: now };

    setNextActionCardCue(null);
    setLoopContinueLine(null);
    applyImmediateNextActionFeedback(action);
    if (
      (action.kind === "failed" || action.kind === "partial") &&
      rid
    ) {
      setResultState("Creating task…");
      scheduleClearNextActionFeedback(12000);
    }
    void (async () => {
      let execResult: ExecuteNextActionResult = { runId: null };
      try {
        execResult = await executeNextAction(action);
        if (
          (action.kind === "failed" || action.kind === "partial") &&
          rid
        ) {
          if (execResult.taskOutcome === "created") {
            setResultState("Task created — now tracked");
            setNextActionCardCue("task_created");
          } else if (execResult.taskOutcome === "failed") {
            setResultState("Could not create — try again");
          } else if (execResult.taskOutcome === "unavailable") {
            setResultState("Action not available yet — opening flow");
          }
          scheduleClearNextActionFeedback(12000);
        }
        if (rid) {
          const vis = await verifyRunAfterAction(rid);
          const sim = new Set(actedRunIds);
          sim.add(rid);
          const afterClick = computeNextAction(runs, sim);
          const applyTaskCreatedLoop = () => {
            if (execResult.taskOutcome === "created") {
              setLoopContinueLine(formatLoopContinueLine(afterClick));
            }
          };
          if (vis) {
            const s = (vis.state || "").toLowerCase();
            const mem: {
              tasksCreated?: number;
              completedFlows?: number;
              resolvedBlockers?: number;
            } = {};
            if (execResult.taskOutcome === "created") mem.tasksCreated = 1;
            if (s === "completed") mem.completedFlows = 1;
            if (
              (action.kind === "failed" || action.kind === "partial") &&
              execResult.taskOutcome !== "created" &&
              (s === "processing" || s === "accepted")
            ) {
              mem.resolvedBlockers = 1;
            }
            if (Object.keys(mem).length > 0) {
              setValueMemory(bumpKirpValueMemory(mem));
            }
            if (s === "completed") {
              setResultState("Done — this is now resolved");
              const pb = formatProofLine(vis);
              setResultProofLine(
                pb !== "Updated just now"
                  ? `${pb} · Flow completed successfully`
                  : "Flow completed successfully",
              );
              setRecentProgress((prev) => {
                const tail = prev.slice(1);
                return ["Completed flow — result ready", ...tail].slice(0, 3);
              });
              applyTaskCreatedLoop();
              scheduleClearNextActionFeedback(1800);
            } else if (execResult.taskOutcome === "created") {
              if (s === "processing" || s === "accepted") {
                setResultProofLine("Flow is continuing · Task tracked");
              } else if (s === "failed") {
                setResultProofLine("Run still blocked — follow-up is in your task");
              } else {
                const pb = formatProofLine(vis);
                setResultProofLine(
                  pb !== "Updated just now" ? `${pb} · Task tracked` : "Task tracked",
                );
              }
              applyTaskCreatedLoop();
              scheduleClearNextActionFeedback(2800);
            } else {
              setResultState(formatVerifiedResultLine(action.kind, vis));
              if (s === "processing" || s === "accepted") {
                setResultProofLine("Flow is continuing");
              } else if (s === "failed") {
                setResultProofLine("Still blocked — needs attention");
              } else {
                setResultProofLine(formatProofLine(vis));
              }
              scheduleClearNextActionFeedback(2800);
            }
          } else {
            applyTaskCreatedLoop();
          }
        }
      } catch {
        if ((action.kind === "failed" || action.kind === "partial") && rid) {
          setResultState("Could not create — try again");
          scheduleClearNextActionFeedback(12000);
        }
      } finally {
        if (rid) {
          setActedRunIds((prev) => {
            const next = new Set(prev);
            next.add(rid);
            return next;
          });
        }
      }
    })();
  };

  return (
    <div className="relative space-y-6" suppressHydrationWarning>
      <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-textMain flex items-center gap-2 flex-wrap">
            <Radio className="h-6 w-6 text-primary" />
            Run monitor
            {alertCount > 0 ? (
              <span
                className="inline-flex items-center gap-1 rounded-full border border-amber-500/50 bg-amber-500/15 px-2.5 py-0.5 text-xs font-semibold text-amber-200"
                title={alertsPayload?.alerts?.[0]?.message ?? "Active alerts"}
              >
                <AlertTriangle className="h-3.5 w-3.5 shrink-0" />
                {alertCount} alert{alertCount === 1 ? "" : "s"}
              </span>
            ) : null}
          </h1>
          <p className="text-sm text-textSoft mt-1 max-w-2xl">
            Tenant-scoped ingest runs from{" "}
            <code className="rounded bg-surface2 px-1 text-xs">
              GET /api/v1/tenant/{"{"}tenant_id{"}"}/runs
            </code>
            . Query{" "}
            <code className="rounded bg-surface2 px-1 text-xs">
              ?tenant=default
            </code>{" "}
            to override the session tenant. Dev server defaults to{" "}
            <strong className="text-textMain">port 3100</strong> (
            <code className="text-xs">npm run dev</code>
            ).
          </p>
          <p className="text-xs text-textSoft mt-2">
            Tenant:{" "}
            <span className="font-mono text-textMain">{tenantId}</span>
            {lastRefresh && (
              <>
                {" "}
                · Last update: {lastRefresh.toLocaleTimeString()}
                {sseLive ? (
                  <span className="ml-2 text-green-400">· SSE stream</span>
                ) : null}
              </>
            )}
          </p>
        </div>
        <button
          type="button"
          onClick={() => void load()}
          className="inline-flex items-center gap-2 self-start rounded-xl border border-[color:var(--color-border-subtle)] bg-surface2 px-3 py-2 text-sm text-textMain hover:bg-surface2/80"
        >
          <RefreshCw className="h-4 w-4" />
          Refresh
        </button>
      </div>

      {error && (
        <div className="rounded-xl border border-red-500/40 bg-red-500/10 px-4 py-3 text-sm text-red-200">
          {error}
        </div>
      )}

      <div
        className={`px-0.5 text-xs font-normal leading-relaxed text-textSoft sm:text-sm ${
          nextAction.kind === "idle" ? "opacity-[0.72]" : ""
        }`}
      >
        <p>{sessionDirection.theme}</p>
        {nextAction.kind === "idle" ? null : (
          <p className="mt-0.5 opacity-90">{sessionDirection.sentence}</p>
        )}
        {weeklyMeaningfulMoves > 0 ? (
          <p className="mt-1 text-[11px] text-textSoft/80">
            This week: {weeklyMeaningfulMoves} meaningful move
            {weeklyMeaningfulMoves === 1 ? "" : "s"}
          </p>
        ) : null}
      </div>

      <Card
        className={cn(
          "rounded-2xl border-[color:var(--color-border-subtle)] bg-surface1/90 transition-[box-shadow,background-color,border-color] duration-500",
          nextActionCardCue === "task_created" &&
            "border-emerald-500/45 bg-emerald-950/15 shadow-[0_0_36px_-12px_rgba(16,185,129,0.5)] ring-1 ring-emerald-500/40",
        )}
      >
        <CardHeader>
          <CardTitle className="text-base text-textMain">Next Action</CardTitle>
          <p className="text-xs text-textSoft">
            One recommended move to keep progress clear and continuous.
          </p>
        </CardHeader>
        <CardContent className="space-y-3">
          {resultState ? (
            <div>
              {progressFlash ? (
                <p className="text-sm font-medium text-textMain">{progressFlash}</p>
              ) : null}
              <p className="text-lg font-semibold text-textMain">{resultState}</p>
              {resultProofLine ? (
                <p className="mt-1 text-xs leading-snug text-textSoft/80">{resultProofLine}</p>
              ) : null}
              {nextActionCardCue === "task_created" ? (
                <div className="mt-3 flex gap-2.5 rounded-xl border border-emerald-500/40 bg-emerald-500/10 px-3 py-2.5">
                  <CheckCircle2
                    className="mt-0.5 h-5 w-5 shrink-0 text-emerald-400"
                    aria-hidden
                  />
                  <div className="min-w-0 space-y-1.5">
                    <p className="text-xs font-medium leading-snug text-emerald-50">
                      Something new now exists — it is in your Tasks list.
                    </p>
                    <Link
                      href="/tasks"
                      className="inline-flex text-xs font-medium text-emerald-200 underline decoration-emerald-400/70 underline-offset-2 hover:text-emerald-100"
                    >
                      Open Tasks to see it
                    </Link>
                  </div>
                </div>
              ) : null}
              {loopContinueLine ? (
                <p className="mt-3 text-sm font-medium leading-snug text-textMain">
                  {loopContinueLine}
                </p>
              ) : (
                <p className="mt-2 text-sm text-textSoft">
                  Preparing your next best move…
                </p>
              )}
            </div>
          ) : (
            <>
              <div>
                <p className="text-lg font-semibold text-textMain">{nextAction.action}</p>
                <p className="mt-1 text-sm text-textSoft">{nextAction.outcome}</p>
              </div>
              <p className="text-xs text-textSoft">{nextAction.impact}</p>
              <p className="text-[11px] text-textSoft">
                Action type:{" "}
                <span className="font-medium text-textMain">
                  {actionExecutionType(nextAction.kind) === "real"
                    ? "Real action (mutates state)"
                    : actionExecutionType(nextAction.kind) === "view_only"
                      ? "View-only (opens run context)"
                      : "Guidance-only (no mutation)"}
                </span>
              </p>
              {clickIntent ? (
                <p className={clickIntent.accentClass}>{clickIntent.line}</p>
              ) : null}
            </>
          )}
          <div>
            <button
              type="button"
              onClick={onNextActionClick}
              disabled={Boolean(resultState)}
              className="inline-flex items-center gap-2 rounded-xl border border-[color:var(--color-border-subtle)] bg-primary px-3 py-2 text-sm font-medium text-white hover:opacity-90"
            >
              {resultState ? "Applying…" : ctaLabelForKind(nextAction.kind)}
            </button>
          </div>
          {!resultState ? (
            <div className="space-y-1 border-t border-[color:var(--color-border-subtle)] pt-3">
              <p
                className={`text-[11px] leading-snug ${
                  nextAction.kind === "idle"
                    ? "text-textSoft opacity-90"
                    : "text-textSoft"
                }`}
              >
                {cardMergedAnchor}
              </p>
              <p className="text-[11px] leading-snug text-textSoft">
                {riskTrustLine(nextAction.kind)}
              </p>
            </div>
          ) : null}
          {!resultState ? (
            <p className="text-[11px] leading-snug text-textSoft">{afterThisLine}</p>
          ) : null}
          {recentProgress.length > 0 && !resultState ? (
            <div className="border-t border-[color:var(--color-border-subtle)] pt-3">
              <p className="text-[10px] font-medium uppercase tracking-wide text-textSoft">
                Recent progress
              </p>
              {progressSummary ? (
                <p className="mt-1.5 text-xs leading-snug text-textSoft">{progressSummary}</p>
              ) : null}
              <ul className="sr-only">
                {recentProgress.map((line, i) => (
                  <li key={`${line}-${i}`}>{line}</li>
                ))}
              </ul>
            </div>
          ) : null}
        </CardContent>
      </Card>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card className="rounded-2xl border-[color:var(--color-border-subtle)] bg-surface1/90">
          <CardHeader>
            <CardTitle className="text-base text-textMain">
              Page stats (completed / partial / failed)
            </CardTitle>
            <p className="text-xs text-textSoft">
              Counts reflect the current page only (limit {LIMIT}), matching
              the API <code className="text-[11px]">stats</code> object.
            </p>
          </CardHeader>
          <CardContent>
            <RunStatsPie stats={stats} />
            <dl className="mt-4 grid grid-cols-2 gap-2 text-sm sm:grid-cols-4">
              <div>
                <dt className="text-textSoft text-xs">total</dt>
                <dd className="font-semibold text-textMain">{stats.total}</dd>
              </div>
              <div>
                <dt className="text-textSoft text-xs">completed</dt>
                <dd className="font-semibold text-green-400">{stats.completed}</dd>
              </div>
              <div>
                <dt className="text-textSoft text-xs">partial</dt>
                <dd className="font-semibold text-amber-300">{stats.partial}</dd>
              </div>
              <div>
                <dt className="text-textSoft text-xs">failed</dt>
                <dd className="font-semibold text-red-400">{stats.failed}</dd>
              </div>
            </dl>
          </CardContent>
        </Card>

        <Card className="rounded-2xl border-[color:var(--color-border-subtle)] bg-surface1/90">
          <CardHeader>
            <CardTitle className="text-base text-textMain">
              Live updates
            </CardTitle>
            <p className="text-xs text-textSoft">
              Server-Sent Events from{" "}
              <code className="text-[11px]">
                /api/v1/tenant/…/runs/stream
              </code>{" "}
              (15s cadence) with Bearer token from the same storage as other
              API calls. Falls back to manual refresh if the stream fails.
            </p>
          </CardHeader>
          <CardContent>
            <ul className="list-disc space-y-1 pl-4 text-sm text-textSoft">
              <li>Open run details: click a row below.</li>
              <li>Timeline loads from{" "}
                <code className="text-[11px]">/api/v1/run/…/status</code>.
              </li>
            </ul>
          </CardContent>
        </Card>
      </div>

      <Card className="rounded-2xl border-[color:var(--color-border-subtle)] bg-surface1/90">
        <CardHeader>
          <CardTitle className="text-base text-textMain">Recent runs</CardTitle>
        </CardHeader>
        <CardContent>
          <RunsTable
            runs={runs}
            onSelectRun={onRowClick}
            selectedRunId={selectedRunId}
          />
        </CardContent>
      </Card>

      <RunDetailModal
        runId={selectedRunId}
        open={modalOpen}
        onOpenChange={setModalOpen}
      />

      {runContextOpen ? (
        <>
          <div
            className="fixed inset-0 z-[90] bg-black/45"
            aria-hidden
            onClick={closeRunContext}
          />
          <aside
            className="fixed inset-y-0 right-0 z-[100] flex min-h-0 w-full max-w-md flex-col border-l border-[color:var(--color-border-subtle)] bg-surface1 shadow-xl"
            role="dialog"
            aria-modal="false"
            aria-labelledby="run-context-title"
          >
            <div className="flex items-start justify-between gap-2 border-b border-[color:var(--color-border-subtle)] px-4 py-3">
              <div className="min-w-0 flex-1">
                <p
                  id="run-context-title"
                  className="truncate font-mono text-sm font-semibold text-textMain"
                  title={runContextRunId ?? ""}
                >
                  {runContextRunId}
                </p>
                <p className="mt-1 text-xs text-textSoft">
                  state:{" "}
                  {runContextData?.state ?? (runContextLoading ? "…" : "—")}
                  {" · "}
                  duration:{" "}
                  {runContextData?.duration_ms != null
                    ? `${runContextData.duration_ms} ms`
                    : "—"}
                </p>
                {runContextLoading ? (
                  <p className="mt-0.5 text-[11px] text-textSoft">Loading details…</p>
                ) : null}
              </div>
              <button
                type="button"
                onClick={closeRunContext}
                className="shrink-0 rounded-lg p-2 text-textSoft hover:bg-surface2 hover:text-textMain"
                aria-label="Close"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
            <div className="min-h-0 flex-1 overflow-y-auto px-4 py-3">
              {runContextLoading ? (
                <div className="space-y-2 text-xs text-textSoft">
                  <div className="h-3 w-[75%] rounded bg-surface2" />
                  <div className="h-3 w-full rounded bg-surface2" />
                  <div className="h-3 w-[83%] rounded bg-surface2" />
                </div>
              ) : null}
              {runContextError ? (
                <p className="text-sm text-red-300">{runContextError}</p>
              ) : null}
              {runContextData && !runContextLoading ? (
                <div id="run-context-steps" className="space-y-2">
                  <p className="text-[11px] font-medium uppercase tracking-wide text-textSoft">
                    Steps
                  </p>
                  <ul className="space-y-2 text-sm">
                    {runContextData.steps.map((s, idx) => (
                      <li
                        key={`${s.name}-${idx}`}
                        id={`run-context-step-${idx}`}
                        className="rounded-lg border border-[color:var(--color-border-subtle)] bg-surface2/50 px-3 py-2"
                      >
                        <p className="font-medium text-textMain">{s.name}</p>
                        <p className="text-xs text-textSoft">
                          {s.status}
                          {s.duration_ms != null ? ` · ${s.duration_ms} ms` : ""}
                        </p>
                      </li>
                    ))}
                  </ul>
                  <div id="run-context-steps-end" className="h-px w-full shrink-0" aria-hidden />
                </div>
              ) : null}
            </div>
            <div
              className={`shrink-0 border-t border-[color:var(--color-border-subtle)] px-4 ${
                panelCTAQuietContext ? "py-5" : "py-3"
              }`}
            >
              {panelShowPersonalizationHint ? (
                <p className="text-xs leading-snug text-textSoft">
                  {getPersonalizationHint(userContextSignals)}
                </p>
              ) : null}
              {panelMergedAnchor ? (
                <p
                  className={`text-xs leading-snug ${
                    panelShowPersonalizationHint ? "mt-2" : "mt-0.5"
                  } ${panelIdleSoft ? "text-textSoft opacity-90" : "text-textMain"}`}
                >
                  {panelMergedAnchor}
                </p>
              ) : null}
              {panelExpectedImpactBullets.length > 0 ? (
                <>
                  <p className="mt-2 text-[10px] font-medium uppercase tracking-wide text-textSoft">
                    This will:
                  </p>
                  <ul className="mt-1.5 list-disc space-y-1 pl-4 text-[11px] leading-snug text-textSoft">
                    {panelExpectedImpactBullets.map((line, i) => (
                      <li key={`impact-${i}`}>{line}</li>
                    ))}
                  </ul>
                </>
              ) : null}
              <p
                className={`text-[10px] font-medium uppercase tracking-wide text-textSoft ${
                  panelCTAQuietContext ? "mt-6" : "mt-4"
                }`}
              >
                Recommended next step
              </p>
              <p className="mt-1 text-sm text-textMain">
                {panelRecommendedLine || "…"}
              </p>
              <button
                type="button"
                onClick={onRunContextPanelContinue}
                className={`inline-flex items-center gap-2 rounded-xl border border-[color:var(--color-border-subtle)] bg-primary px-3 py-2 text-sm font-medium text-white hover:opacity-90 ${
                  panelCTAQuietContext ? "mt-4" : "mt-3"
                }`}
              >
                {ctaLabelForKind(panelActionKind)}
              </button>
              {panelCTAQuietContext ? (
                <p className="mt-2 max-w-[18rem] text-xs leading-snug text-textSoft/70">
                  {quietReassuranceLine(runContextRunId)}
                </p>
              ) : null}
            </div>
          </aside>
        </>
      ) : null}
    </div>
  );
}

export default function MonitoringPage() {
  return (
    <Suspense fallback={<PageSkeleton title subtitle cards={2} tableRows={6} />}>
      <MonitoringContent />
    </Suspense>
  );
}
