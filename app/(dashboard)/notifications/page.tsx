"use client";

import React, { useCallback, useEffect, useState } from "react";
import { apiClient, type NotificationV1 } from "@/lib/apiClient";
import { DEFAULT_TENANT_ID, DEFAULT_USER_ID } from "@/lib/constants";
import { NotificationCard } from "@/components/notifications/NotificationCard";
import { Button } from "@/components/ui/button";
import { CheckCheck, Loader2 } from "lucide-react";

const TABS = [
  { key: "all", label: "All" },
  { key: "task_created", label: "Tasks" },
  { key: "commitment_due", label: "Commitments" },
  { key: "agent_action", label: "Agents" },
  { key: "insight_generated", label: "Insights" },
  { key: "sync_error", label: "System" },
];

function filterByTab(list: NotificationV1[], tab: string): NotificationV1[] {
  if (tab === "all") return list;
  if (tab === "task_created") return list.filter((n) => n.type.startsWith("task"));
  if (tab === "sync_error") return list.filter((n) => n.type === "sync_error" || n.type === "connection_issue");
  return list.filter((n) => n.type === tab);
}

export default function NotificationsPage() {
  const [notifications, setNotifications] = useState<NotificationV1[]>([]);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState("all");
  const tenant_id = DEFAULT_TENANT_ID;
  const user_id = DEFAULT_USER_ID;

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const list = await apiClient.listNotificationsV1({
        tenant_id,
        user_id,
        limit: 100,
        type: tab === "all" ? undefined : tab === "task_created" ? undefined : tab === "sync_error" ? undefined : tab,
      });
      setNotifications(list);
    } finally {
      setLoading(false);
    }
  }, [tab]);

  useEffect(() => {
    load();
  }, [load]);

  const handleMarkRead = useCallback(async (id: string) => {
    await apiClient.markNotificationReadV1(id);
    setNotifications((prev) => prev.map((n) => (n.id === id ? { ...n, read: true } : n)));
  }, []);

  const handleMarkAllRead = useCallback(async () => {
    await apiClient.markAllNotificationsReadV1({ tenant_id, user_id });
    setNotifications((prev) => prev.map((n) => ({ ...n, read: true })));
  }, [tenant_id, user_id]);

  const list = filterByTab(notifications, tab);

  return (
    <div className="flex flex-col gap-4 p-4">
      <div className="flex flex-col gap-1">
        <h1 className="text-xl font-semibold text-textMain">Activity Center</h1>
        <p className="text-sm text-textSoft">Notifications and activity across tasks, commitments, and agents.</p>
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap gap-2">
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
        <Button size="sm" variant="outline" onClick={handleMarkAllRead}>
          <CheckCheck className="h-4 w-4 mr-1" />
          Mark all as read
        </Button>
      </div>

      <div className="min-h-[200px]">
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-textSoft" />
          </div>
        ) : (
          <div className="space-y-2">
            {list.map((n) => (
              <NotificationCard
                key={n.id}
                notification={n}
                onMarkRead={handleMarkRead}
              />
            ))}
          </div>
        )}
        {!loading && list.length === 0 && (
          <p className="py-12 text-center text-sm text-textSoft">No notifications.</p>
        )}
      </div>
    </div>
  );
}
