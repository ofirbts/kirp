"use client";

import { create } from "zustand";

interface AgentSelectionState {
  selectedAgentId?: string;
  setSelectedAgent: (id?: string) => void;
}

export const useAgentSelectionStore = create<AgentSelectionState>((set) => ({
  selectedAgentId: undefined,
  setSelectedAgent: (id) => set({ selectedAgentId: id }),
}));

