"use client";

import React from "react";
import type { NotificationV1 } from "@/lib/apiClient";
import {
  CheckCircle2,
  Calendar,
  Bell,
  Lightbulb,
  Zap,
  AlertCircle,
  Link2,
  ListTodo,
} from "lucide-react";

const TYPE_ICONS: Record<string, React.ComponentType<{ className?: string }>> = {
  task_created: ListTodo,
  task_updated: ListTodo,
  commitment_due: Calendar,
  commitment_overdue: AlertCircle,
  reminder: Bell,
  insight_generated: Lightbulb,
  agent_action: Zap,
  sync_error: AlertCircle,
  connection_issue: Link2,
};

function formatDate(s: string | null | undefined): string {
  if (!s) return "";
  try {
    return new Date(s).toLocaleString(undefined, { dateStyle: "short", timeStyle: "short" });
  } catch {
    return String(s);
  }
}

export function NotificationCard({
  notification,
  onMarkRead,
  onClick,
}: {
  notification: NotificationV1;
  onMarkRead?: (id: string) => void;
  onClick?: (n: NotificationV1) => void;
}) {
  const Icon = TYPE_ICONS[notification.type] ?? Bell;
  const href = notification.entity_id
    ? notification.type.startsWith("task")
      ? "/tasks"
      : notification.type.startsWith("commitment")
        ? "/tasks"
        : undefined
    : undefined;

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={() => {
        onClick?.(notification);
        if (notification.entity_id && href) {
          window.location.href = href;
        }
      }}
      onKeyDown={(e) => {
        if (e.key === "Enter") {
          onClick?.(notification);
          if (href) window.location.href = href;
        }
      }}
      className={
        notification.read
          ? "flex gap-3 rounded-xl border border-[color:var(--color-border-subtle)] bg-surface2/50 p-3 text-left transition-colors"
          : "flex gap-3 rounded-xl border border-[color:var(--color-border-strong)] bg-surface2 p-3 text-left transition-colors"
      }
    >
      <div className="shrink-0 rounded-lg bg-surface3 p-2">
        <Icon className="h-4 w-4 text-textMain" />
      </div>
      <div className="min-w-0 flex-1">
        <p className="font-medium text-textMain">{notification.title}</p>
        <p className="text-sm text-textSoft line-clamp-2">{notification.body}</p>
        <p className="mt-1 text-xs text-textSoft">{formatDate(notification.created_at)}</p>
      </div>
      {!notification.read && onMarkRead && (
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            onMarkRead(notification.id);
          }}
          className="shrink-0 rounded p-1 text-textSoft hover:bg-surface3 hover:text-textMain"
          title="Mark as read"
        >
          <CheckCircle2 className="h-4 w-4" />
        </button>
      )}
    </div>
  );
}
