"use client";

import { useEffect, useRef } from "react";
import { getNotificationsWsUrl } from "@/lib/apiClient";
import { useNotificationStore } from "@/lib/stores/notificationStore";
import { useAuthStore } from "@/lib/stores/authStore";
import { DEFAULT_TENANT_ID, DEFAULT_USER_ID } from "@/lib/constants";

const RECONNECT_INITIAL_MS = 1000;
const RECONNECT_MAX_MS = 30000;

/** WebSocket for notifications. Uses authenticated user's tenant_id and user_id when available. */
export function useNotificationsWs(tenantId?: string | null, userId?: string | null) {
  const { user } = useAuthStore();
  const effectiveTenantId = tenantId ?? user?.tenant_id ?? DEFAULT_TENANT_ID;
  const effectiveUserId = userId ?? user?.id ?? DEFAULT_USER_ID;

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const reconnectMsRef = useRef(RECONNECT_INITIAL_MS);
  const setUnreadCount = useNotificationStore((s) => s.setUnreadCount);
  const setPulse = useNotificationStore((s) => s.setPulse);

  useEffect(() => {
    const url = `${getNotificationsWsUrl()}?tenant_id=${encodeURIComponent(
      effectiveTenantId
    )}&user_id=${encodeURIComponent(effectiveUserId)}`;

    let closed = false;

    function connect() {
      if (closed) return;
      try {
        const ws = new WebSocket(url);
        wsRef.current = ws;

        ws.onopen = () => {
          reconnectMsRef.current = RECONNECT_INITIAL_MS;
        };

        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data as string) as {
              type?: string;
              unread_count?: number;
            };
            if (data.type === "unread_count" && typeof data.unread_count === "number") {
              setUnreadCount(data.unread_count);
            } else if (data.type === "notification") {
              if (typeof data.unread_count === "number") setUnreadCount(data.unread_count);
              else setUnreadCount(useNotificationStore.getState().unreadCount + 1);
              setPulse(true);
              setTimeout(() => setPulse(false), 2000);
            }
          } catch {
            // ignore parse errors
          }
        };

        ws.onclose = () => {
          wsRef.current = null;
          if (closed) return;
          const ms = reconnectMsRef.current;
          reconnectTimeoutRef.current = setTimeout(() => {
            reconnectMsRef.current = Math.min(ms * 2, RECONNECT_MAX_MS);
            connect();
          }, ms);
        };

        ws.onerror = () => {
          // close will fire and trigger reconnect
        };
      } catch {
        reconnectTimeoutRef.current = setTimeout(connect, reconnectMsRef.current);
      }
    }

    connect();

    return () => {
      closed = true;
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = null;
      }
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [effectiveTenantId, effectiveUserId, setUnreadCount, setPulse]);
}
