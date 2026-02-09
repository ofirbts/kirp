"use client";

import React, { useCallback, useEffect, useState } from "react";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { NotificationCard } from "./NotificationCard";
import { apiClient, type NotificationV1 } from "@/lib/apiClient";
import { DEFAULT_TENANT_ID, DEFAULT_USER_ID } from "@/lib/constants";
import { useAuthStore } from "@/lib/stores/authStore";
import { CheckCheck, Loader2 } from "lucide-react";

const TABS = [
  { key: "all", label: "All" },
  { key: "task_created", label: "Tasks" },
  { key: "commitment_due", label: "Commitments" },
  { key: "agent_action", label: "Agents" },
  { key: "insight_generated", label: "Insights" },
  { key: "sync_error", label: "System" },
];

export function NotificationPanel({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const { user } = useAuthStore();
  const [notifications, setNotifications] = useState<NotificationV1[]>([]);
  const [loading, setLoading] = useState(false);
  const [tab, setTab] = useState("all");
  const tenant_id = user?.tenant_id ?? DEFAULT_TENANT_ID;
  const user_id = user?.id ?? DEFAULT_USER_ID;

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const needAll = tab === "all" || tab === "task_created" || tab === "sync_error";
      const list = await apiClient.listNotificationsV1({
        tenant_id,
        user_id,
        limit: 50,
        type: needAll ? undefined : tab,
      });
      setNotifications(list);
    } finally {
      setLoading(false);
    }
  }, [tab, tenant_id, user_id]);

  useEffect(() => {
    if (open) load();
  }, [open, load]);

  const handleMarkRead = useCallback(
    async (id: string) => {
      await apiClient.markNotificationReadV1(id);
      setNotifications((prev) => prev.map((n) => (n.id === id ? { ...n, read: true } : n)));
    },
    []
  );

  const handleMarkAllRead = useCallback(async () => {
    await apiClient.markAllNotificationsReadV1({ tenant_id, user_id });
    setNotifications((prev) => prev.map((n) => ({ ...n, read: true })));
  }, [tenant_id, user_id]);

  const tasksFilter = tab === "task_created" ? (n: NotificationV1) => n.type.startsWith("task") : (n: NotificationV1) => n.type === tab;
  const systemFilter = (n: NotificationV1) => n.type === "sync_error" || n.type === "connection_issue";
  const list =
    tab === "all"
      ? notifications
      : tab === "task_created"
        ? notifications.filter(tasksFilter)
        : tab === "sync_error"
          ? notifications.filter(systemFilter)
          : notifications.filter((n) => n.type === tab);

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="w-full max-w-md overflow-y-auto bg-surface1 border-l border-[color:var(--color-border-subtle)]">
        <SheetHeader>
          <SheetTitle className="text-textMain">Activity Center</SheetTitle>
        </SheetHeader>
        <div className="mt-4 flex justify-end">
          <Button size="sm" variant="outline" onClick={handleMarkAllRead}>
            <CheckCheck className="h-4 w-4 mr-1" />
            Mark all as read
          </Button>
        </div>
        <div className="mt-3 flex flex-wrap gap-2">
          {TABS.map((t) => (
            <button
              key={t.key}
              type="button"
              onClick={() => setTab(t.key)}
              className={`rounded-full px-3 py-1.5 text-xs font-medium ${
                tab === t.key ? "bg-primary text-bg" : "bg-surface2 text-textMain hover:bg-surface3"
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>
        <div className="mt-4 space-y-2">
          {loading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-6 w-6 animate-spin text-textSoft" />
            </div>
          ) : (
            list.map((n) => (
              <NotificationCard
                key={n.id}
                notification={n}
                onMarkRead={handleMarkRead}
              />
            ))
          )}
        </div>
        {!loading && list.length === 0 && (
          <p className="py-8 text-center text-sm text-textSoft">No notifications.</p>
        )}
      </SheetContent>
    </Sheet>
  );
}
