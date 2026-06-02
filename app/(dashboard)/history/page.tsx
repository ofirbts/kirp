"use client";

import React, { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import {
  Mail,
  MessageCircle,
  Slack,
  ListTodo,
  CheckCircle2,
  Calendar,
  FolderOpen,
  Lightbulb,
  Zap,
  FileText,
  CalendarDays,
  AlertCircle,
} from "lucide-react";
import { apiClient, type HistoryEntryV1 } from "@/lib/apiClient";
import { DEFAULT_TENANT_ID } from "@/lib/constants";
import { useAuthStore } from "@/lib/stores/authStore";
import { ErrorState } from "@/components/feedback/ErrorState";

const TYPE_ICONS: Record<string, React.ComponentType<{ className?: string }>> = {
  email_received: Mail,
  whatsapp_message: MessageCircle,
  slack_message: Slack,
  task_created: ListTodo,
  task_completed: CheckCircle2,
  task_updated: ListTodo,
  commitment_created: Calendar,
  commitment_due: CalendarDays,
  project_updated: FolderOpen,
  agent_insight: Lightbulb,
  agent_action: Zap,
  notion_sync: FileText,
  calendar_event: CalendarDays,
  system: AlertCircle,
};

const FILTERS = [
  { key: "all", label: "All" },
  { key: "messages", label: "Messages", types: ["email_received", "whatsapp_message", "slack_message"] },
  { key: "tasks", label: "Tasks", types: ["task_created", "task_completed", "task_updated"] },
  { key: "commitments", label: "Commitments", types: ["commitment_created", "commitment_due"] },
  { key: "projects", label: "Projects", types: ["project_updated"] },
  { key: "agents", label: "Agents", types: ["agent_insight", "agent_action"] },
  { key: "system", label: "System", types: ["system"] },
];

const PAGE_SIZE = 30;

function formatTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" });
  } catch {
    return String(iso);
  }
}

function formatDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleDateString(undefined, { dateStyle: "short" });
  } catch {
    return String(iso);
  }
}

function getDateGroup(iso: string | null | undefined): "today" | "yesterday" | "this_week" | "older" {
  if (!iso) return "older";
  const d = new Date(iso);
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const yesterday = new Date(today);
  yesterday.setDate(yesterday.getDate() - 1);
  const weekAgo = new Date(today);
  weekAgo.setDate(weekAgo.getDate() - 7);
  const dDate = new Date(d.getFullYear(), d.getMonth(), d.getDate());
  if (dDate.getTime() === today.getTime()) return "today";
  if (dDate.getTime() === yesterday.getTime()) return "yesterday";
  if (dDate.getTime() >= weekAgo.getTime()) return "this_week";
  return "older";
}

const GROUP_LABELS: Record<string, string> = {
  today: "Today",
  yesterday: "Yesterday",
  this_week: "This Week",
  older: "Older",
};

function groupByDate(entries: HistoryEntryV1[]): Map<string, HistoryEntryV1[]> {
  const map = new Map<string, HistoryEntryV1[]>();
  const order = ["today", "yesterday", "this_week", "older"];
  for (const key of order) {
    map.set(key, []);
  }
  for (const e of entries) {
    const group = getDateGroup(e.created_at);
    map.get(group)?.push(e);
  }
  return map;
}

function getEntityHref(entry: HistoryEntryV1): string | null {
  if (!entry.entity_id) return null;
  const t = entry.type;
  if (t === "task_created" || t === "task_completed") return "/tasks";
  if (t === "commitment_created" || t === "commitment_due") return "/tasks";
  if (t === "project_updated") return "/tasks";
  if (t === "calendar_event") return "/events";
  return null;
}

export default function HistoryPage() {
  const router = useRouter();
  const { user, loaded } = useAuthStore();
  const [entries, setEntries] = useState<HistoryEntryV1[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState("all");
  const [hasMore, setHasMore] = useState(true);

  const skipAuth = process.env.NEXT_PUBLIC_SKIP_AUTH === "1";
  const tenant_id = user?.tenant_id ?? DEFAULT_TENANT_ID;
  const user_id = user?.id ?? null;

  const typeFilter = useMemo(() => FILTERS.find((f) => f.key === filter), [filter]);
  const apiType = typeFilter?.types?.length === 1 ? typeFilter.types[0] : undefined;

  const load = useCallback(
    async (append: boolean, toTimestamp?: string | null) => {
      if (!user_id && !skipAuth) return;
      if (append) setLoadingMore(true);
      else setLoading(true);
      setError(null);
      try {
        const list = await apiClient.listHistoryV1({
          tenant_id,
          user_id: user_id ?? undefined,
          limit: PAGE_SIZE,
          type: apiType,
          to: toTimestamp || undefined,
        });
        if (append) {
          setEntries((prev) => {
            const seen = new Set(prev.map((e) => e.id));
            const newOnes = list.filter((e) => !seen.has(e.id));
            return [...prev, ...newOnes];
          });
        } else {
          setEntries(list);
        }
        setHasMore(list.length >= PAGE_SIZE);
      } catch (e) {
        const msg = e instanceof Error ? e.message : "Could not load history.";
        setError(msg);
      } finally {
        setLoading(false);
        setLoadingMore(false);
      }
    },
    [tenant_id, user_id, skipAuth, apiType]
  );

  useEffect(() => {
    if (loaded && (user || skipAuth)) load(false);
  }, [load, loaded, user, skipAuth, filter]);

  const loadMore = useCallback(() => {
    if (entries.length === 0) return;
    const last = entries[entries.length - 1];
    load(true, last.created_at ?? undefined);
  }, [entries, load]);

  const filtered = useMemo(
    () =>
      filter === "all" || !typeFilter?.types
        ? entries
        : entries.filter((e) => typeFilter.types!.includes(e.type)),
    [entries, filter, typeFilter]
  );

  const grouped = useMemo(() => groupByDate(filtered), [filtered]);

  if (!loaded) {
    return (
      <div className="flex flex-col gap-4 p-4">
        <p className="py-8 text-center text-sm text-textSoft">Loading history…</p>
      </div>
    );
  }
  if (loaded && !user && !skipAuth) {
    return (
      <div className="flex flex-col gap-4 p-4">
        <p className="py-8 text-center text-sm text-textSoft">Loading history…</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4 p-4">
      <div className="flex flex-col gap-1">
        <h1 className="text-2xl font-bold tracking-tight text-textMain">History</h1>
        <p className="text-sm text-textSoft">
          Human-readable timeline of your activity: messages, tasks, commitments, and more.
        </p>
      </div>

      <div className="flex flex-wrap gap-2">
        {FILTERS.map((f) => (
          <button
            key={f.key}
            type="button"
            onClick={() => setFilter(f.key)}
            className={`rounded-full px-3 py-1.5 text-xs font-medium ${
              filter === f.key ? "bg-primary text-bg" : "bg-surface2 text-textMain hover:bg-surface3"
            }`}
          >
            {f.label}
          </button>
        ))}
      </div>

      {error && <ErrorState message={error} onRetry={() => load(false)} />}

      {!error && loading && (
        <p className="py-8 text-center text-sm text-textSoft">Loading…</p>
      )}

      {!error && !loading && (
        <div className="timeline flex flex-col gap-6">
          {["today", "yesterday", "this_week", "older"].map((groupKey) => {
            const groupEntries = grouped.get(groupKey) || [];
            if (groupEntries.length === 0) return null;
            return (
              <div key={groupKey}>
                <h2 className="mb-3 text-sm font-semibold text-textSoft">
                  {GROUP_LABELS[groupKey]}
                </h2>
                <div className="space-y-2">
                  {groupEntries.map((entry) => {
                    const Icon = TYPE_ICONS[entry.type] ?? AlertCircle;
                    const href = getEntityHref(entry);
                    return (
                      <button
                        key={entry.id}
                        type="button"
                        onClick={() => {
                          if (href) router.push(href);
                        }}
                        className="flex w-full gap-3 rounded-xl border border-[color:var(--color-border-subtle)] bg-surface2 p-3 text-left transition-colors hover:border-primary/40 hover:bg-surface3"
                      >
                        <div className="shrink-0 rounded-lg bg-surface3 p-2">
                          <Icon className="h-4 w-4 text-textMain" />
                        </div>
                        <div className="min-w-0 flex-1">
                          <p className="font-medium text-textMain">{entry.title}</p>
                          <p className="text-sm text-textSoft line-clamp-2">{entry.body}</p>
                          <p className="mt-1 text-xs text-textSoft">
                            {formatTime(entry.created_at)}
                            {groupKey === "older" && ` · ${formatDate(entry.created_at)}`}
                          </p>
                        </div>
                      </button>
                    );
                  })}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {!error && !loading && filtered.length === 0 && (
        <p className="py-12 text-center text-sm text-textSoft">
          No history yet. Activity from tasks, messages, and agents will appear here.
        </p>
      )}

      {!error && !loading && hasMore && filtered.length > 0 && (
        <div className="flex justify-center py-4">
          <button
            type="button"
            onClick={loadMore}
            disabled={loadingMore}
            className="rounded-full bg-surface2 px-4 py-2 text-sm font-medium text-textMain hover:bg-surface3 disabled:opacity-50"
          >
            {loadingMore ? "Loading…" : "Load more"}
          </button>
        </div>
      )}
    </div>
  );
}
