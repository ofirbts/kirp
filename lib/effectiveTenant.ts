import { DEFAULT_TENANT_ID } from "@/lib/constants";

export function isSkipAuthClientMode(): boolean {
  if (typeof process === "undefined") return false;
  const skip = process.env.NEXT_PUBLIC_SKIP_AUTH === "1";
  const env = (process.env.NEXT_PUBLIC_ENV || process.env.NODE_ENV || "").toLowerCase();
  return skip || env === "development" || env === "local";
}

export function resolveTenantForApi(
  userTenant?: string | null,
  storeTenant?: string | null,
): string {
  const explicit = (userTenant || storeTenant || "").trim();
  if (explicit) return explicit;
  if (isSkipAuthClientMode()) return DEFAULT_TENANT_ID;
  throw new Error("tenant_id required — sign in or set tenant context");
}
