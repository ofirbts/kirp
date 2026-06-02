"use client";

import { create } from "zustand";

interface AuditFiltersState {
  actorOrAction: string;
  setActorOrAction: (value: string) => void;
}

export const useAuditFiltersStore = create<AuditFiltersState>((set) => ({
  actorOrAction: "",
  setActorOrAction: (actorOrAction) => set({ actorOrAction }),
}));

