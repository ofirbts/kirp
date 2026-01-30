"use client";

import { create } from "zustand";

interface EventSelectionState {
  selectedEventId?: string;
  isEventDrawerOpen: boolean;
  openEvent: (id: string) => void;
  closeEvent: () => void;
}

export const useEventSelectionStore = create<EventSelectionState>((set) => ({
  selectedEventId: undefined,
  isEventDrawerOpen: false,
  openEvent: (id) => set({ selectedEventId: id, isEventDrawerOpen: true }),
  closeEvent: () => set({ isEventDrawerOpen: false }),
}));

