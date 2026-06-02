"use client";

import { create } from "zustand";
import type { Event } from "@/lib/types";
import { apiClient } from "@/lib/apiClient";

interface LiveEventStreamState {
  events: Event[];
  loading: boolean;
  error?: string;
  lastUpdatedAt?: string;
  refresh: (tenantId?: string, spaceId?: string, signal?: AbortSignal) => Promise<void>;
}

export const useLiveEventStreamStore = create<LiveEventStreamState>((set) => ({
  events: [],
  loading: false,
  error: undefined,
  lastUpdatedAt: undefined,
  async refresh(tenantId?: string, spaceId?: string, signal?: AbortSignal) {
    const controller = signal ? undefined : new AbortController();
    const effectiveSignal = signal ?? controller?.signal;
    set({ loading: true, error: undefined });
    try {
      const res = await apiClient.listEvents({
        tenantId,
        spaceId,
      });
      if (effectiveSignal?.aborted) return;
      set({
        events: res.data ?? [],
        loading: false,
        error: undefined,
        lastUpdatedAt: new Date().toISOString(),
      });
    } catch (err) {
      if (effectiveSignal?.aborted) return;
      set({
        loading: false,
        error: err instanceof Error ? err.message : "Failed to load events",
      });
    }
  },
}));

