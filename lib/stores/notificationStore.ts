"use client";

import { create } from "zustand";

interface NotificationState {
  unreadCount: number;
  setUnreadCount: (n: number) => void;
  pulse: boolean;
  setPulse: (p: boolean) => void;
}

export const useNotificationStore = create<NotificationState>((set) => ({
  unreadCount: 0,
  setUnreadCount: (n) => set({ unreadCount: Math.max(0, n) }),
  pulse: false,
  setPulse: (p) => set({ pulse: p }),
}));
