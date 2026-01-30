"use client";

import { create } from "zustand";

interface EventsFiltersState {
  topic: string;
  setTopic: (topic: string) => void;
}

export const useEventsFiltersStore = create<EventsFiltersState>((set) => ({
  topic: "",
  setTopic: (topic) => set({ topic }),
}));

