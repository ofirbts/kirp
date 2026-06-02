"use client";
import { useMemo, useCallback, useEffect, useState, Suspense } from "react";
import { apiClient, type TaskV1 } from "@/lib/apiClient";
import type { SchemaNodeV1 } from "@/lib/apiClient";
import { DEFAULT_TENANT_ID } from "@/lib/constants";
import { useTenantContextStore } from "@/lib/stores/tenantContextStore";
import { useAuthStore } from "@/lib/stores/authStore";
import { PageSkeleton } from "@/components/dashboard/PageSkeleton";
import { ErrorState } from "@/components/feedback/ErrorState";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import {
  CheckCircle2,
  Calendar,
  ListTodo,
  FolderOpen,
  LayoutGrid,
  Plus,
  Pencil,
  Clock,
  ArrowRight,
  AlertCircle,
  GripVertical,
} from "lucide-react";

const LIFE_AREAS = ["Work", "Family", "Health", "Learning"];
const STATUS_OPTIONS = ["pending", "in_progress", "completed", "blocked"];

function formatDate(s: string | null | undefined): string {
  if (!s) return "—";
  try {
    const d = new Date(s);
    return d.toLocaleDateString(undefined, { dateStyle: "short", timeZone: "UTC" });
  } catch {
    return String(s);
  }
}

function formatDateFull(s: string | null | undefined): string {
  if (!s) return "";
  try {
    return new Date(s).toISOString().slice(0, 16);
  } catch {
    return String(s);
  }
}

function isToday(iso: string | null | undefined): boolean {
  if (!iso) return false;
  const d = new Date(iso);
  const today = new Date();
  return d.getUTCDate() === today.getUTCDate() && d.getUTCMonth() === today.getUTCMonth() && d.getUTCFullYear() === today.getUTCFullYear();
}

function isOverdue(iso: string | null | undefined): boolean {
  if (!iso) return false;
  return new Date(iso) < new Date();
}

function snoozeDueDate(iso: string | null | undefined): string {
  const d = iso ? new Date(iso) : new Date();
  d.setDate(d.getDate() + 1);
  d.setHours(9, 0, 0, 0);
  return d.toISOString().slice(0, 19);
}

type ViewKey = "today" | "upcoming" | "overdue" | "completed" | "projects" | "lifearea";

export default function TasksPage() {
  const { tenantId, spaceId } = useTenantContextStore();
  const { user, loaded } = useAuthStore();
  const [tasks, setTasks] = useState<TaskV1[]>([]);
  const [nodes, setNodes] = useState<SchemaNodeV1[]>([]);
  const [commitments, setCommitments] = useState<SchemaNodeV1[]>([]);
  const [projects, setProjects] = useState<SchemaNodeV1[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [view, setView] = useState<ViewKey>("today");
  const [quickAdd, setQuickAdd] = useState("");
  const [adding, setAdding] = useState(false);
  const [editId, setEditId] = useState<string | null>(null);
  const [editNode, setEditNode] = useState<SchemaNodeV1 | null>(null);
  const [editForm, setEditForm] = useState({ title: "", due_date: "", status: "", priority: "", description: "" });
  const [saving, setSaving] = useState(false);
  const [dragOverId, setDragOverId] = useState<string | null>(null);
  const [taskOrder, setTaskOrder] = useState<string[]>([]);

  const skipAuth = process.env.NEXT_PUBLIC_SKIP_AUTH === "1";
  const tenant_id = tenantId ?? DEFAULT_TENANT_ID;

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [tasksRes, nodesRes] = await Promise.all([
        apiClient.listTasksV1({
          tenant_id,
          space_id: spaceId ?? "all",
          limit: 500,
        }),
        apiClient.listNodesV1({
          tenant_id,
          space_id: spaceId ?? "all",
          limit: 500,
        }),
      ]);
      const taskList = (tasksRes.data ?? []).slice();
      taskList.sort((a, b) => {
        const da = a.due_date ? new Date(a.due_date).getTime() : null;
        const db = b.due_date ? new Date(b.due_date).getTime() : null;
        if (da == null && db == null) return 0;
        if (da == null) return 1;
        if (db == null) return -1;
        return da - db;
      });
      setTasks(taskList);
      setTaskOrder(taskList.map((t) => t.id));
      const allNodes = nodesRes.data ?? [];
      setNodes(allNodes);
      setCommitments(allNodes.filter((n) => n.entity === "commitment"));
      setProjects(allNodes.filter((n) => n.entity === "project"));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load tasks");
    } finally {
      setLoading(false);
    }
  }, [tenant_id, spaceId]);

  useEffect(() => {
    if (loaded && (user || skipAuth)) load();
  }, [load, loaded, user, skipAuth]);

  const handleQuickAdd = useCallback(async () => {
    if (!quickAdd.trim()) return;
    setAdding(true);
    try {
      await apiClient.createTaskV1(
        { title: quickAdd.trim() },
        { tenant_id: tenant_id, space_id: spaceId ?? "all", user_id: user?.id }
      );
      setQuickAdd("");
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to add task");
    } finally {
      setAdding(false);
    }
  }, [quickAdd, tenant_id, spaceId, load, user?.id]);

  const openEdit = useCallback(
    async (id: string) => {
      setEditId(id);
      try {
        const res = await apiClient.getNodeV1(id, { tenant_id: tenant_id });
        const n = res.node;
        setEditNode(n);
        setEditForm({
          title: n.title ?? "",
          due_date: n.due_date ? formatDateFull(n.due_date) : "",
          status: n.status ?? "pending",
          priority: n.priority ?? "",
          description: n.description ?? "",
        });
      } catch {
        setEditId(null);
      }
    },
    [tenant_id]
  );

  const saveEdit = useCallback(async () => {
    if (!editId) return;
    setSaving(true);
    try {
      await apiClient.updateNodeV1(
        editId,
        {
          title: editForm.title || "Untitled",
          due_date: editForm.due_date ? new Date(editForm.due_date).toISOString().slice(0, 19) + "Z" : undefined,
          status: editForm.status || undefined,
          priority: editForm.priority || undefined,
          description: editForm.description || undefined,
        },
        { tenant_id: tenant_id, user_id: user?.id }
      );
      setEditId(null);
      setEditNode(null);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to save");
    } finally {
      setSaving(false);
    }
  }, [editId, editForm, tenant_id, load, user?.id]);

  const markComplete = useCallback(
    async (id: string) => {
      try {
        await apiClient.updateNodeV1(id, { status: "completed" }, { tenant_id: tenant_id, user_id: user?.id });
        await load();
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to update");
      }
    },
    [tenant_id, load, user?.id]
  );

  const snooze = useCallback(
    async (id: string) => {
      const t = tasks.find((x) => x.id === id);
      const next = snoozeDueDate(t?.due_date ?? null);
      try {
        await apiClient.updateNodeV1(id, { due_date: next }, { tenant_id: tenant_id, user_id: user?.id });
        await load();
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to snooze");
      }
    },
    [tasks, tenant_id, load, user?.id]
  );

  const convertToProject = useCallback(
    async (taskId: string) => {
      const t = tasks.find((x) => x.id === taskId);
      if (!t) return;
      try {
        const createRes = await apiClient.createNodeV1(
          { entity: "project", title: t.title ?? "New project" },
          { tenant_id: tenant_id, space_id: spaceId ?? "all", user_id: user?.id }
        );
        const projectId = createRes.node?.id;
        if (projectId) {
          await apiClient.updateNodeV1(taskId, { parent_id: projectId }, { tenant_id: tenant_id, user_id: user?.id });
        }
        await load();
      } catch (e) {
        setError(e instanceof Error ? e.message : "Convert failed");
      }
    },
    [tasks, tenant_id, spaceId, load, user?.id]
  );

  const convertToCommitment = useCallback(
    async (taskId: string) => {
      const t = tasks.find((x) => x.id === taskId);
      if (!t) return;
      try {
        await apiClient.createNodeV1(
          {
            entity: "commitment",
            title: t.title ?? "New commitment",
            due_date: t.due_date ?? undefined,
            status: t.status ?? undefined,
          },
          { tenant_id: tenant_id, space_id: spaceId ?? "all", user_id: user?.id }
        );
        await apiClient.updateNodeV1(taskId, { status: "completed" }, { tenant_id: tenant_id, user_id: user?.id });
        await load();
      } catch (e) {
        setError(e instanceof Error ? e.message : "Convert failed");
      }
    },
    [tasks, tenant_id, spaceId, load, user?.id]
  );

  const filteredTasks = useMemo(() => {
    const list = taskOrder.length
      ? taskOrder.map((id) => tasks.find((t) => t.id === id)).filter(Boolean) as TaskV1[]
      : tasks;
    if (view === "today") {
      return list.filter((t) => isToday(t.due_date) && t.status !== "completed");
    }
    if (view === "upcoming") {
      return list.filter((t) => t.due_date && !isToday(t.due_date) && !isOverdue(t.due_date) && t.status !== "completed");
    }
    if (view === "overdue") {
      return list.filter((t) => isOverdue(t.due_date) && t.status !== "completed");
    }
    if (view === "completed") {
      return list.filter((t) => t.status === "completed");
    }
    if (view === "lifearea") {
      return list;
    }
    return list;
  }, [tasks, taskOrder, view]);
  const openWithoutDueDateCount = useMemo(
    () => tasks.filter((t) => t.status !== "completed" && !t.due_date).length,
    [tasks]
  );

  const tasksByProject = useMemo(
    () =>
      view === "projects"
        ? projects.map((proj) => ({
            project: proj,
            tasks: tasks.filter((t) => nodes.find((n) => n.id === t.id)?.parent_id === proj.id),
          }))
        : [],
    [view, projects, tasks, nodes]
  );

  const getRisk = (due: string | null | undefined, status: string | null | undefined) => {
    if (status === "blocked") return "blocked";
    if (!due) return null;
    const d = new Date(due);
    const now = new Date();
    if (d < now) return "late";
    const days = (d.getTime() - now.getTime()) / (24 * 60 * 60 * 1000);
    if (days <= 2) return "at_risk";
    return null;
  };

  if (!loaded) {
    return <PageSkeleton title subtitle tableRows={8} />;
  }
  if (loaded && !user && !skipAuth) {
    return <PageSkeleton title subtitle tableRows={8} />;
  }

  if (loading && tasks.length === 0) {
    return <PageSkeleton title subtitle tableRows={8} />;
  }

  if (error) {
    return (
      <div className="space-y-6" suppressHydrationWarning>
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-textMain">Tasks</h1>
          <p className="mt-1 text-sm text-textSoft">Manage tasks, commitments, and projects.</p>
        </div>
        <ErrorState message={error} onRetry={load} />
      </div>
    );
  }

  return (
    <div className="space-y-6" suppressHydrationWarning>
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between" suppressHydrationWarning>
        <div suppressHydrationWarning>
          <h1 className="text-2xl font-bold tracking-tight text-textMain">Tasks & Commitments</h1>
          <p className="mt-1 text-sm text-textSoft">Today, upcoming, overdue, and by project or life area.</p>
        </div>
        <Button size="sm" variant="outline" className="rounded-full" onClick={() => load()}>
          Refresh
        </Button>
      </div>

      {/* Quick Add */}
      <div className="flex flex-wrap items-center gap-2 rounded-2xl border border-[color:var(--color-border-subtle)] bg-surface1/90 p-3">
        <input
          type="text"
          placeholder="Quick add task…"
          value={quickAdd}
          onChange={(e) => setQuickAdd(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleQuickAdd()}
          className="min-w-[200px] flex-1 rounded-xl border border-[color:var(--color-border-subtle)] bg-surface2 px-3 py-2 text-sm text-textMain placeholder:text-textSoft"
        />
        <Button size="sm" className="rounded-xl" onClick={handleQuickAdd} disabled={adding || !quickAdd.trim()}>
          <Plus className="h-4 w-4 mr-1" />
          Add
        </Button>
      </div>

      {/* Tabs */}
      <div className="flex flex-wrap gap-2 border-b border-[color:var(--color-border-subtle)] pb-2">
        {(
          [
            { key: "today" as ViewKey, label: "Today", icon: Calendar },
            { key: "upcoming" as ViewKey, label: "Upcoming", icon: ListTodo },
            { key: "overdue" as ViewKey, label: "Overdue", icon: AlertCircle },
            { key: "completed" as ViewKey, label: "Completed", icon: CheckCircle2 },
            { key: "projects" as ViewKey, label: "By Project", icon: FolderOpen },
            { key: "lifearea" as ViewKey, label: "By Life Area", icon: LayoutGrid },
          ] as const
        ).map(({ key, label, icon: Icon }) => (
          <button
            key={key}
            type="button"
            onClick={() => setView(key)}
            className={`flex items-center gap-2 rounded-full px-4 py-2 text-sm font-medium transition-colors ${
              view === key
                ? "bg-primary text-bg"
                : "bg-surface2 text-textMain hover:bg-surface3"
            }`}
          >
            <Icon className="h-4 w-4" />
            {label}
          </button>
        ))}
      </div>

      {/* Task list */}
      {(view === "today" || view === "upcoming" || view === "overdue" || view === "completed" || view === "lifearea") && (
        <Card className="rounded-2xl border border-[color:var(--color-border-subtle)] bg-surface1/90 shadow-soft">
          <CardHeader>
            <CardTitle className="text-base text-textMain">
              {view === "today" && "Due today"}
              {view === "upcoming" && "Upcoming"}
              {view === "overdue" && "Overdue"}
              {view === "completed" && "Completed"}
              {view === "lifearea" && "All tasks"}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2">
              {filteredTasks.map((t) => (
                <li
                  key={t.id}
                  draggable
                  onDragStart={(e) => {
                    e.dataTransfer.setData("text/plain", t.id);
                    e.dataTransfer.effectAllowed = "move";
                  }}
                  onDragOver={(e) => {
                    e.preventDefault();
                    setDragOverId(t.id);
                  }}
                  onDragLeave={() => setDragOverId(null)}
                  onDrop={(e) => {
                    e.preventDefault();
                    setDragOverId(null);
                    const fromId = e.dataTransfer.getData("text/plain");
                    if (!fromId || fromId === t.id) return;
                    const idx = taskOrder.indexOf(fromId);
                    const toIdx = taskOrder.indexOf(t.id);
                    if (idx === -1 || toIdx === -1) return;
                    const next = [...taskOrder];
                    next.splice(idx, 1);
                    next.splice(toIdx, 0, fromId);
                    setTaskOrder(next);
                  }}
                  className={`flex items-center gap-3 rounded-xl border p-3 transition-colors ${
                    dragOverId === t.id ? "border-primary bg-primary/10" : "border-[color:var(--color-border-subtle)] bg-surface2/50"
                  }`}
                >
                  <GripVertical className="h-4 w-4 text-textSoft shrink-0 cursor-grab" />
                  <button
                    type="button"
                    onClick={() => t.status !== "completed" && markComplete(t.id)}
                    className="shrink-0 rounded-full border-2 border-[color:var(--color-border-strong)] w-6 h-6 flex items-center justify-center"
                  >
                    {t.status === "completed" && <CheckCircle2 className="h-4 w-4 text-green-500" />}
                  </button>
                  <div className="min-w-0 flex-1">
                    <p className={`text-sm font-medium text-textMain ${t.status === "completed" ? "line-through text-textSoft" : ""}`}>
                      {t.title || "—"}
                    </p>
                    <p className="text-xs text-textSoft">
                      {formatDate(t.due_date)} · {t.source ?? "—"} · {t.status ?? "pending"}
                    </p>
                  </div>
                  <div className="flex items-center gap-1 shrink-0">
                    <Button size="sm" variant="ghost" className="h-8 w-8 p-0" onClick={() => openEdit(t.id)} title="Edit">
                      <Pencil className="h-4 w-4" />
                    </Button>
                    {t.status !== "completed" && (
                      <>
                        <Button size="sm" variant="ghost" className="h-8 w-8 p-0" onClick={() => snooze(t.id)} title="Snooze">
                          <Clock className="h-4 w-4" />
                        </Button>
                        <Button size="sm" variant="ghost" className="h-8 w-8 p-0" onClick={() => convertToProject(t.id)} title="Convert to project">
                          <FolderOpen className="h-4 w-4" />
                        </Button>
                        <Button size="sm" variant="ghost" className="h-8 w-8 p-0" onClick={() => convertToCommitment(t.id)} title="Convert to commitment">
                          <ArrowRight className="h-4 w-4" />
                        </Button>
                      </>
                    )}
                  </div>
                </li>
              ))}
            </ul>
            {filteredTasks.length === 0 && (
              <p className="py-8 text-center text-sm text-textSoft">
                {view === "today" && openWithoutDueDateCount > 0
                  ? `No tasks are due today. You still have ${openWithoutDueDateCount} open task(s) without a due date.`
                  : "No tasks in this view."}
              </p>
            )}
          </CardContent>
        </Card>
      )}

      {/* By Project */}
      {view === "projects" && (
        <div className="space-y-4">
          {tasksByProject.map(({ project, tasks: projTasks }) => (
            <Card key={project.id} className="rounded-2xl border border-[color:var(--color-border-subtle)] bg-surface1/90 shadow-soft">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle className="text-base text-textMain">{project.title}</CardTitle>
                  <span className="text-xs text-textSoft">
                    {projTasks.filter((t) => t.status === "completed").length} / {projTasks.length} tasks
                  </span>
                </div>
                {project.description && (
                  <p className="text-sm text-textSoft mt-1">{project.description}</p>
                )}
                <div className="h-2 rounded-full bg-surface2 mt-2 overflow-hidden">
                  <div
                    className="h-full bg-primary transition-all"
                    style={{
                      width: projTasks.length ? `${(100 * projTasks.filter((t) => t.status === "completed").length) / projTasks.length}%` : "0%",
                    }}
                  />
                </div>
              </CardHeader>
              <CardContent>
                <ul className="space-y-2">
                  {projTasks.map((t) => (
                    <li key={t.id} className="flex items-center gap-3 rounded-lg border border-[color:var(--color-border-subtle)] p-2">
                      <button
                        type="button"
                        onClick={() => t.status !== "completed" && markComplete(t.id)}
                        className="shrink-0 rounded-full border-2 w-5 h-5 flex items-center justify-center"
                      >
                        {t.status === "completed" && <CheckCircle2 className="h-4 w-4 text-green-500" />}
                      </button>
                      <span className={`text-sm ${t.status === "completed" ? "line-through text-textSoft" : "text-textMain"}`}>{t.title}</span>
                      <span className="text-xs text-textSoft ml-auto">{formatDate(t.due_date)}</span>
                      <Button size="sm" variant="ghost" className="h-7 w-7 p-0" onClick={() => openEdit(t.id)}><Pencil className="h-3 w-3" /></Button>
                    </li>
                  ))}
                </ul>
                {projTasks.length === 0 && <p className="text-sm text-textSoft py-2">No tasks in this project.</p>}
              </CardContent>
            </Card>
          ))}
          {tasksByProject.length === 0 && (
            <p className="py-8 text-center text-sm text-textSoft">No projects yet. Convert a task to a project.</p>
          )}
        </div>
      )}

      {/* Commitments */}
      <Card className="rounded-2xl border border-[color:var(--color-border-subtle)] bg-surface1/90 shadow-soft">
        <CardHeader>
          <CardTitle className="text-base text-textMain">Commitments</CardTitle>
          <p className="text-xs text-textSoft">Due date, owner, and risk (late / at risk / blocked).</p>
        </CardHeader>
        <CardContent>
          <ul className="space-y-3">
            {commitments.slice(0, 20).map((c) => {
              const risk = getRisk(c.due_date ?? null, c.status ?? null);
              const meta = (c.metadata ?? {}) as Record<string, string>;
              return (
                <li key={c.id} className="flex items-center justify-between gap-4 rounded-xl border border-[color:var(--color-border-subtle)] p-3 bg-surface2/50">
                  <div>
                    <p className="font-medium text-textMain">{c.title}</p>
                    <p className="text-xs text-textSoft">
                      Due: {formatDate(c.due_date)} · Owner: {meta.owner ?? "—"} · Source: {meta.source ?? "—"}
                    </p>
                  </div>
                  {risk && (
                    <span
                      className={`shrink-0 rounded-full px-2 py-1 text-xs font-medium ${
                        risk === "late" ? "bg-red-500/20 text-red-400" : risk === "at_risk" ? "bg-amber-500/20 text-amber-400" : "bg-neutral-500/20 text-neutral-400"
                      }`}
                    >
                      {risk === "late" ? "Late" : risk === "at_risk" ? "At risk" : "Blocked"}
                    </span>
                  )}
                  <Button size="sm" variant="ghost" className="h-8 w-8 p-0" onClick={() => openEdit(c.id)}><Pencil className="h-4 w-4" /></Button>
                </li>
              );
            })}
          </ul>
          {commitments.length === 0 && <p className="text-sm text-textSoft py-4">No commitments yet. Convert a task to a commitment.</p>}
        </CardContent>
      </Card>

      {/* Edit modal */}
      <Dialog open={!!editId} onOpenChange={(open: boolean) => { if (!open) setEditId(null); }}>
        <DialogContent className="rounded-2xl border border-[color:var(--color-border-subtle)] bg-surface1 text-textMain">
          <DialogHeader>
            <DialogTitle>Edit task</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div>
              <label className="text-xs font-medium text-textSoft">Title</label>
              <input
                value={editForm.title}
                onChange={(e) => setEditForm((f) => ({ ...f, title: e.target.value }))}
                className="mt-1 w-full rounded-xl border border-[color:var(--color-border-subtle)] bg-surface2 px-3 py-2 text-sm text-textMain"
              />
            </div>
            <div>
              <label className="text-xs font-medium text-textSoft">Due date</label>
              <input
                type="datetime-local"
                value={editForm.due_date}
                onChange={(e) => setEditForm((f) => ({ ...f, due_date: e.target.value }))}
                className="mt-1 w-full rounded-xl border border-[color:var(--color-border-subtle)] bg-surface2 px-3 py-2 text-sm text-textMain"
              />
            </div>
            <div>
              <label className="text-xs font-medium text-textSoft">Status</label>
              <Select value={editForm.status} onValueChange={(v) => setEditForm((f) => ({ ...f, status: v }))}>
                <SelectTrigger className="mt-1 bg-surface2 text-textMain">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {STATUS_OPTIONS.map((s) => (
                    <SelectItem key={s} value={s}>{s}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <label className="text-xs font-medium text-textSoft">Description</label>
              <textarea
                value={editForm.description}
                onChange={(e) => setEditForm((f) => ({ ...f, description: e.target.value }))}
                rows={3}
                className="mt-1 w-full rounded-xl border border-[color:var(--color-border-subtle)] bg-surface2 px-3 py-2 text-sm text-textMain"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setEditId(null)}>Cancel</Button>
            <Button onClick={saveEdit} disabled={saving}>Save</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
