"use client";

import { useEffect, useRef } from "react";
import type { TenantRunsResponse } from "@/lib/apiClient";

const BASE =
  (typeof process !== "undefined" && process.env?.NEXT_PUBLIC_API_URL) ||
  "http://localhost:8000";

function getRuntimeToken(): string | null {
  if (typeof window === "undefined") return null;
  const fromLocal =
    window.localStorage.getItem("access_token") ??
    window.localStorage.getItem("kirp_auth_token") ??
    window.localStorage.getItem("kirp_token");
  const fromSession =
    window.sessionStorage.getItem("access_token") ??
    window.sessionStorage.getItem("kirp_auth_token") ??
    window.sessionStorage.getItem("kirp_token");
  const dev = typeof process !== "undefined" ? process.env?.NEXT_PUBLIC_DEV_TOKEN ?? "" : "";
  return fromLocal || fromSession || dev || null;
}

/**
 * Consume FastAPI text/event-stream (SSE) with Authorization header via fetch + ReadableStream.
 */
export function useTenantRunsStream(
  tenantId: string | null,
  limit: number,
  enabled: boolean,
  onPayload: (data: TenantRunsResponse) => void,
): void {
  const onPayloadRef = useRef(onPayload);
  onPayloadRef.current = onPayload;

  useEffect(() => {
    if (!enabled || !tenantId) return;

    const url = new URL(
      `/api/v1/tenant/${encodeURIComponent(tenantId)}/runs/stream`,
      BASE,
    );
    url.searchParams.set("limit", String(limit));

    const headers: Record<string, string> = {
      Accept: "text/event-stream",
    };
    const token = getRuntimeToken();
    if (token) {
      headers.Authorization = `Bearer ${token}`;
    }

    const ac = new AbortController();
    let cancelled = false;

    async function run() {
      try {
        const res = await fetch(url.toString(), {
          method: "GET",
          headers,
          credentials: "include",
          signal: ac.signal,
        });
        if (!res.ok || !res.body) {
          return;
        }
        const reader = res.body.getReader();
        const dec = new TextDecoder();
        let buffer = "";
        while (!cancelled) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += dec.decode(value, { stream: true });
          const chunks = buffer.split("\n\n");
          buffer = chunks.pop() ?? "";
          for (const block of chunks) {
            const line = block.split("\n").find((l) => l.startsWith("data: "));
            if (!line) continue;
            const json = line.slice(6).trim();
            if (!json) continue;
            try {
              const parsed = JSON.parse(json) as TenantRunsResponse;
              if (parsed?.tenant_id && Array.isArray(parsed.runs) && parsed.stats) {
                onPayloadRef.current(parsed);
              }
            } catch {
              /* ignore malformed frame */
            }
          }
        }
      } catch {
        /* abort or network — polling on page covers fallback */
      }
    }

    void run();
    return () => {
      cancelled = true;
      ac.abort();
    };
  }, [tenantId, limit, enabled]);
}
