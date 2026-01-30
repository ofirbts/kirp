"use client";

import { create } from "zustand";

interface TenantContextState {
  tenantId?: string;
  spaceId?: string;
  setTenant: (tenantId?: string) => void;
  setSpace: (spaceId?: string) => void;
}

function getInitialTenantContext(): Pick<TenantContextState, "tenantId" | "spaceId"> {
  if (typeof window === "undefined") {
    return { tenantId: undefined, spaceId: undefined };
  }
  const tenantId = window.localStorage.getItem("kirp_tenant_id") || undefined;
  const spaceId = window.localStorage.getItem("kirp_space_id") || undefined;
  return { tenantId, spaceId };
}

export const useTenantContextStore = create<TenantContextState>((set) => ({
  ...getInitialTenantContext(),
  setTenant: (tenantId) =>
    set((prev) => {
      if (typeof window !== "undefined") {
        if (tenantId) {
          window.localStorage.setItem("kirp_tenant_id", tenantId);
        } else {
          window.localStorage.removeItem("kirp_tenant_id");
        }
        // Reset space when tenant changes to avoid cross-tenant leakage.
        window.localStorage.removeItem("kirp_space_id");
      }
      return { ...prev, tenantId, spaceId: undefined };
    }),
  setSpace: (spaceId) =>
    set((prev) => {
      if (typeof window !== "undefined") {
        if (spaceId) {
          window.localStorage.setItem("kirp_space_id", spaceId);
        } else {
          window.localStorage.removeItem("kirp_space_id");
        }
      }
      return { ...prev, spaceId };
    }),
}));

