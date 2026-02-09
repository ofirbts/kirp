/**
 * Fallback values for SKIP_AUTH=1 / local dev only.
 * For authenticated flows: use user from auth store (user.tenant_id, user.id) ONLY.
 * Do NOT use these as fallbacks for ingest, history, or any multi-tenant API calls.
 */
export const DEFAULT_TENANT_ID = "default";
/** @deprecated Use user.id from auth store. Only for SKIP_AUTH display fallback. */
export const DEFAULT_USER_ID = "dev";
