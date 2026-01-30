"use client";

import { create } from "zustand";
import { apiClient } from "@/lib/apiClient";

export type AuthUser = {
  id: string;
  email: string;
  name: string;
};

type AuthState = {
  user: AuthUser | null;
  token: string | null;
  loggingIn: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
};

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  token: null,
  loggingIn: false,
  async login(email: string, password: string) {
    set({ loggingIn: true });
    try {
      // We don't yet have a typed login API; call a backend helper if present.
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const clientAsAny = apiClient as any;
      if (typeof clientAsAny.login === "function") {
        const res = await clientAsAny.login({ email, password });
        const token = res.token ?? null;
        const user = res.user ?? { id: "unknown", email, name: email };

        // Persist JWT token for subsequent API calls.
        if (token) {
          if (typeof window !== "undefined") {
            window.localStorage.setItem("kirp_auth_token", token);
          }
        } else if (typeof window !== "undefined") {
          window.localStorage.removeItem("kirp_auth_token");
        }

        set({ user, token, loggingIn: false });
        return;
      }

      // Fallback: demo-only local login without real auth.
      set({
        user: { id: "demo", email, name: email },
        token: null,
        loggingIn: false,
      });
    } catch {
      set({ loggingIn: false });
      throw new Error("Login failed. Check backend logs or credentials.");
    }
  },
  logout() {
    if (typeof window !== "undefined") {
      window.localStorage.removeItem("kirp_auth_token");
    }
    set({ user: null, token: null });
  },
}));

