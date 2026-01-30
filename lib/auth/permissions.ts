"use client";

import { useAuthStore } from "@/lib/stores/authStore";

export type Resource =
  | "agents"
  | "workflows"
  | "users"
  | "tenants"
  | "spaces"
  | "audit"
  | "events";

export type Action = "read" | "write" | "execute" | "admin";

/**
 * Minimal, client-side permissions helper for the new dashboard.
 *
 * For now we intentionally avoid any backend calls and default to:
 * - read-only for anonymous users
 * - read-only for authenticated users until a real RBAC model is wired.
 */
export function useCan() {
  const { user } = useAuthStore();

  function can(_resource: Resource, action: Action): boolean {
    // No user → read-only demo mode.
    if (!user) {
      return action === "read";
    }
    // Authenticated user → keep UI safe and simple: read-only until RBAC is implemented.
    return action === "read";
  }

  return {
    can,
    loading: false,
    error: null as string | null,
  };
}

