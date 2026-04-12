"use client";

import { create } from "zustand";
import { DEFAULT_TENANT_ID, DEFAULT_USER_ID } from "@/lib/constants";

interface TenantContextState {
  tenantId: string;
  spaceId: string | null;
  userId: string;
  setTenant: (tenantId: string | null) => void;
  setSpace: (spaceId: string | null) => void;
  setUserId: (userId: string | null) => void;
}

/** Single identity for the whole app. setTenant/setUserId are no-ops; no API or localStorage may override. */
export const useTenantContextStore = create<TenantContextState>((set) => ({
  tenantId: DEFAULT_TENANT_ID,
  spaceId: null,
  userId: DEFAULT_USER_ID,

  setTenant: () => {
    // No-op: tenant is always DEFAULT_TENANT_ID. Do not persist or read from localStorage.
  },

  setSpace: (spaceId) =>
    set(() => {
      if (typeof window !== "undefined") {
        if (spaceId) localStorage.setItem("kirp_space_id", spaceId);
        else localStorage.removeItem("kirp_space_id");
      }
      return { spaceId };
    }),

  setUserId: () => {
    // No-op: user is always DEFAULT_USER_ID.
  },
}));

// On client: restore space only. Tenant/user come from AppShell + auth (JWT), not forced DEFAULT here
// (forcing default caused /api/v1/tenant/default/* 403 when JWT tenant was a real UUID).
if (typeof window !== "undefined") {
  localStorage.removeItem("kirp_tenant_id");
  localStorage.removeItem("kirp_user_id");
  const spaceId = localStorage.getItem("kirp_space_id") || "all";
  useTenantContextStore.setState({ spaceId });
}
