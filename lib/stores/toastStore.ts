"use client";

import { create } from "zustand";

export type ToastVariant = "default" | "success" | "error" | "warning";

export type Toast = {
  id: string;
  title?: string;
  description?: string;
  variant?: ToastVariant;
};

interface ToastState {
  toasts: Toast[];
  show: (toast: Omit<Toast, "id">) => void;
  dismiss: (id: string) => void;
}

export const useToastStore = create<ToastState>((set, get) => ({
  toasts: [],
  show: (toast) => {
    const id = `toast_${Date.now()}_${Math.random().toString(16).slice(2)}`;
    const next = { id, ...toast };
    set({ toasts: [...get().toasts, next] });
    // Auto-dismiss after 5s
    setTimeout(() => {
      get().dismiss(id);
    }, 5000);
  },
  dismiss: (id) => {
    set({ toasts: get().toasts.filter((t) => t.id !== id) });
  },
}));

