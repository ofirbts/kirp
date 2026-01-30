"use client";

import React from "react";
import { useRouter } from "next/navigation";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { useAuthStore } from "@/lib/stores/authStore";
import { useToastStore } from "@/lib/stores/toastStore";

export default function Page() {
  const router = useRouter();
  const { login, loggingIn } = useAuthStore();
  const { show } = useToastStore();

  const [email, setEmail] = React.useState("");
  const [password, setPassword] = React.useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim() || !password.trim()) {
      show({
        variant: "warning",
        title: "Missing credentials",
        description: "Please enter both email and password.",
      });
      return;
    }
    try {
      await login(email.trim(), password.trim());
      show({
        variant: "success",
        title: "Signed in",
        description: `You are now signed in as ${email.trim()}.`,
      });
      router.push("/");
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Login failed. Please try again.";
      show({
        variant: "error",
        title: "Login failed",
        description: message,
      });
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-neutral-950 px-4">
      <Card className="w-full max-w-sm border-neutral-800 bg-neutral-900/90 px-5 py-6 text-sm shadow-lg shadow-cyan-500/10">
        <h1 className="text-base font-semibold text-neutral-100">
          Sign in to KIRP
        </h1>
        <p className="mt-1 text-xs text-neutral-500">
          This is an authentication scaffold. Once a real login API is wired,
          credentials will be validated against the backend.
        </p>
        <form onSubmit={handleSubmit} className="mt-4 space-y-3">
          <div>
            <label className="block text-xs font-medium text-neutral-300">
              Email
            </label>
            <Input
              type="email"
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="mt-1 h-8 border-neutral-700 bg-neutral-900 text-xs text-neutral-100 placeholder:text-neutral-500"
              placeholder="operator@kirp.local"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-neutral-300">
              Password
            </label>
            <Input
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="mt-1 h-8 border-neutral-700 bg-neutral-900 text-xs text-neutral-100 placeholder:text-neutral-500"
              placeholder="••••••••"
            />
          </div>
          <Button
            type="submit"
            disabled={loggingIn}
            className="mt-2 h-8 w-full bg-cyan-600 text-xs font-medium text-neutral-50 hover:bg-cyan-500"
          >
            {loggingIn ? "Signing in…" : "Sign in"}
          </Button>
        </form>
      </Card>
    </div>
  );
}

