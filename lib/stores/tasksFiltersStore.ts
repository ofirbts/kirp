"use client";

import { create } from "zustand";

interface TasksFiltersState {
  queue: string;
  setQueue: (queue: string) => void;
}

export const useTasksFiltersStore = create<TasksFiltersState>((set) => ({
  queue: "",
  setQueue: (queue) => set({ queue }),
}));

