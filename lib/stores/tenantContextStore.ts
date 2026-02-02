"use client";

import { create } from "zustand";

interface TenantContextState {
  tenantId: string | null;
  spaceId: string | null;
  setTenant: (tenantId: string | null) => void;
  setSpace: (spaceId: string | null) => void;
}

export const useTenantContextStore = create<TenantContextState>((set) => ({
  tenantId: null,
  spaceId: null,

  setTenant: (tenantId) =>
    set(() => {
      if (typeof window !== "undefined") {
        if (tenantId) {
          localStorage.setItem("kirp_tenant_id", tenantId);
        } else {
          localStorage.removeItem("kirp_tenant_id");
        }
      }
      return { tenantId, spaceId: null };
    }),

  setSpace: (spaceId) =>
    set(() => {
      if (typeof window !== "undefined") {
        if (spaceId) {
          localStorage.setItem("kirp_space_id", spaceId);
        } else {
          localStorage.removeItem("kirp_space_id");
        }
      }
      return { spaceId };
    }),
}));

// Load initial values on client only
if (typeof window !== "undefined") {
  const tenantId = localStorage.getItem("kirp_tenant_id") || "default";
  const spaceId = localStorage.getItem("kirp_space_id") || "all";

  useTenantContextStore.setState({ tenantId, spaceId });
}