"use client";

import { create } from "zustand";
import { apiClient, type AuthUserV1 } from "@/lib/apiClient";

type AuthState = {
  user: AuthUserV1 | null;
  token: string | null;
  loggingIn: boolean;
  loaded: boolean;
  login: (email: string, password: string) => Promise<void>;
  signup: (email: string, password: string, name: string) => Promise<void>;
  logout: () => void;
  loadUser: () => Promise<void>;
};

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  token: null,
  loggingIn: false,
  loaded: false,
  async login(email: string, password: string) {
    set({ loggingIn: true });
    try {
      const res = await apiClient.loginV1({ email, password });
      const token = res.access_token ?? null;
      const user = res.user;
      if (typeof window !== "undefined") {
        if (token) {
          window.localStorage.setItem("access_token", token);
        } else {
          window.localStorage.removeItem("access_token");
        }
      }
      set({ user, token, loggingIn: false, loaded: true });
    } catch (err) {
      set({ loggingIn: false });
      throw err instanceof Error ? err : new Error("Login failed");
    }
  },
  async signup(email: string, password: string, name: string) {
    set({ loggingIn: true });
    try {
      const res = await apiClient.signupV1({ email, password, name });
      const token = res.access_token ?? null;
      const user = res.user;
      if (typeof window !== "undefined") {
        if (token) {
          window.localStorage.setItem("access_token", token);
        } else {
          window.localStorage.removeItem("access_token");
        }
      }
      set({ user, token, loggingIn: false, loaded: true });
    } catch (err) {
      set({ loggingIn: false });
      throw err instanceof Error ? err : new Error("Signup failed");
    }
  },
  logout() {
    if (typeof window !== "undefined") {
      window.localStorage.removeItem("access_token");
    }
    set({ user: null, token: null, loaded: true });
  },
  async loadUser() {
    if (typeof window === "undefined") {
      set({ loaded: true });
      return;
    }
  
    const token = window.localStorage.getItem("access_token");
    const skipAuth = process.env.NEXT_PUBLIC_SKIP_AUTH === "1";
  
    // No token → SKIP_AUTH mode
    if (!token) {
      if (skipAuth) {
        try {
          const me = await apiClient.meV1();
          set({ user: me, token: null, loaded: true });
          return;
        } catch {
          set({ user: null, token: null, loaded: true });
        }
      } else {
        set({ user: null, token: null, loaded: true });
      }
      return;
    }

    try {
      const me = await apiClient.meV1();
      set({ user: me, token, loaded: true });
    } catch {
      window.localStorage.removeItem("access_token");
      set({ user: null, token: null, loaded: true });
    }
  }
  
}));
