"use client";

import { create } from "zustand";

interface TaskSelectionState {
  selectedTaskId?: string;
  isTaskDrawerOpen: boolean;
  openTask: (id: string) => void;
  closeTask: () => void;
}

export const useTaskSelectionStore = create<TaskSelectionState>((set) => ({
  selectedTaskId: undefined,
  isTaskDrawerOpen: false,
  openTask: (id) => set({ selectedTaskId: id, isTaskDrawerOpen: true }),
  closeTask: () => set({ isTaskDrawerOpen: false }),
}));

