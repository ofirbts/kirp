// Redis client adapter for KIRP Intelligence OS (V1)
// --------------------------------------------------
// In the current architecture, Redis primarily backs task queues and
// idempotency. For the UI, the source of truth is:
//   - /api/tasks
//
// This module keeps a minimal cache interface (for components that may
// rely on it) and also exposes helpers that surface Redis-backed state
// via the tasks API.

"use client";

import { apiClient } from "@/lib/apiClient";
import type { Task, ListTasksResponse } from "@/lib/types";

const MEMORY_CACHE = new Map<string, { value: unknown; expiresAt?: number }>();

/**
 * Read-through cache helper. In V1 this uses an in-memory map in the browser,
 * but it can be backed by a real Redis-facing HTTP API in future versions.
 */
export async function getCache<T>(key: string): Promise<T | null> {
  const entry = MEMORY_CACHE.get(key);
  if (!entry) return null;
  if (entry.expiresAt && entry.expiresAt < Date.now()) {
    MEMORY_CACHE.delete(key);
    return null;
  }
  return entry.value as T;
}

export async function setCache<T>(
  key: string,
  value: T,
  ttlSeconds?: number,
): Promise<void> {
  const expiresAt =
    typeof ttlSeconds === "number" ? Date.now() + ttlSeconds * 1000 : undefined;
  MEMORY_CACHE.set(key, { value, expiresAt });

  // If the backend exposes a cache API (e.g. /api/cache), forward the write.
  try {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const clientAsAny = apiClient as any;
    if (typeof clientAsAny.setCacheEntry === "function") {
      await clientAsAny.setCacheEntry(key, value, ttlSeconds);
    }
  } catch {
    // Best-effort only; UI remains functional with local cache.
  }
}

export async function deleteCache(key: string): Promise<void> {
  MEMORY_CACHE.delete(key);
  try {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const clientAsAny = apiClient as any;
    if (typeof clientAsAny.deleteCacheEntry === "function") {
      await clientAsAny.deleteCacheEntry(key);
    }
  } catch {
    // Ignore backend cache errors for now.
  }
}

/**
 * Fetch a snapshot of tasks, which reflects the Redis-backed queues
 * through the HTTP API. This is the recommended way for UI components
 * to reason about Redis-related state.
 */
export async function fetchTaskSnapshot(): Promise<Task[]> {
  const res: ListTasksResponse = await apiClient.listTasks({});
  return res.data ?? [];
}


