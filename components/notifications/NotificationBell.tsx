"use client";

import React, { useEffect, useState } from "react";
import { Bell } from "lucide-react";
import { useNotificationStore } from "@/lib/stores/notificationStore";
import { NotificationPanel } from "./NotificationPanel";
import { apiClient } from "@/lib/apiClient";
import { DEFAULT_TENANT_ID, DEFAULT_USER_ID } from "@/lib/constants";
import { useNotificationsWs } from "@/lib/hooks/useNotificationsWs";
import { useAuthStore } from "@/lib/stores/authStore";

export function NotificationBell() {
  const { user } = useAuthStore();
  const unreadCount = useNotificationStore((s) => s.unreadCount);
  const pulse = useNotificationStore((s) => s.pulse);
  const [panelOpen, setPanelOpen] = useState(false);

  useNotificationsWs();

  useEffect(() => {
    let cancelled = false;
    const tenant_id = user?.tenant_id ?? DEFAULT_TENANT_ID;
    const user_id = user?.id ?? DEFAULT_USER_ID;
    apiClient
      .getUnreadCountV1({ tenant_id, user_id })
      .then((n) => {
        if (!cancelled) useNotificationStore.getState().setUnreadCount(n);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [user?.tenant_id, user?.id]);

  return (
    <>
      <button
        type="button"
        onClick={() => setPanelOpen(true)}
        className={`relative inline-flex h-8 w-8 items-center justify-center rounded-full border border-[color:var(--color-border-subtle)] bg-surface2 text-textSoft hover:border-primary/60 hover:text-primary ${pulse ? "animate-pulse ring-2 ring-primary/50" : ""}`}
        title="Activity Center"
      >
        <Bell className="h-4 w-4" />
        {unreadCount > 0 && (
          <span className="absolute -right-0.5 -top-0.5 inline-flex h-3 w-3 min-w-[12px] items-center justify-center rounded-full bg-red-500 px-0.5 text-[9px] font-semibold text-white">
            {unreadCount > 99 ? "99" : unreadCount}
          </span>
        )}
      </button>
      <NotificationPanel open={panelOpen} onOpenChange={setPanelOpen} />
    </>
  );
}
