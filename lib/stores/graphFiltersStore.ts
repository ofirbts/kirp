"use client";

import { create } from "zustand";
import type { GraphNodeType } from "@/lib/types";

interface GraphFiltersState {
  nodeType: GraphNodeType | "all";
  setNodeType: (type: GraphNodeType | "all") => void;
}

export const useGraphFiltersStore = create<GraphFiltersState>((set) => ({
  nodeType: "all",
  setNodeType: (nodeType) => set({ nodeType }),
}));

