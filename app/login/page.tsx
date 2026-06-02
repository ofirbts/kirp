"use client";

import React from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { useAuthStore } from "@/lib/stores/authStore";
import { useToastStore } from "@/lib/stores/toastStore";

export default function Page() {
  const router = useRouter();
  const { login, loadUser, loggingIn, user, loaded } = useAuthStore();
  const { show } = useToastStore();
  const skipAuth = process.env.NEXT_PUBLIC_SKIP_AUTH === "1";

  const [email, setEmail] = React.useState("");
  const [password, setPassword] = React.useState("");

  // In SKIP_AUTH mode: load dev user on mount and redirect when ready
  React.useEffect(() => {
    if (!skipAuth) return;
    loadUser();
  }, [skipAuth, loadUser]);

  React.useEffect(() => {
    if (skipAuth && loaded && user) {
      router.replace("/");
    }
  }, [skipAuth, loaded, user, router]);

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
    <div className="flex min-h-screen items-center justify-center bg-bg px-4">
      <Card className="w-full max-w-sm border-[color:var(--color-border-subtle)] bg-surface1 px-5 py-6 text-sm shadow-soft">
        <h1 className="text-base font-semibold text-textMain">
          Sign in to KIRP
        </h1>
        <p className="mt-1 text-xs text-textSoft">
          Enter your credentials to access your KIRP workspace.
        </p>
        {(process.env.NODE_ENV === "development" ||
          (process.env.NEXT_PUBLIC_API_URL || "").includes("localhost")) && (
          <p className="mt-2 text-xs text-textSoft rounded-md bg-surface2/80 px-2 py-1.5 border border-border/60">
            <span className="font-medium text-textMain">Local Docker stack:</span> the API seeds{" "}
            <code className="text-[11px]">dev@localhost</code> with password{" "}
            <code className="text-[11px]">devdevdev</code> when Mongo is empty. Or set{" "}
            <code className="text-[11px]">SKIP_AUTH=1</code> in <code className="text-[11px]">.env.prod</code> and{" "}
            <code className="text-[11px]">NEXT_PUBLIC_SKIP_AUTH=1</code> in <code className="text-[11px]">.env.local</code>{" "}
            (see <code className="text-[11px]">deploy/README.md</code>).
          </p>
        )}
        <form onSubmit={handleSubmit} className="mt-4 space-y-3">
          <div>
            <label className="block text-xs font-medium text-textMain">
              Email
            </label>
            <Input
              type="email"
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="mt-1 h-8 border-[color:var(--color-border-subtle)] bg-surface2 text-xs text-textMain placeholder:text-textSoft"
              placeholder="operator@kirp.local"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-textMain">
              Password
            </label>
            <Input
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="mt-1 h-8 border-[color:var(--color-border-subtle)] bg-surface2 text-xs text-textMain placeholder:text-textSoft"
              placeholder="••••••••"
            />
          </div>
          <Button
            type="submit"
            disabled={loggingIn}
            className="mt-2 h-8 w-full text-xs font-medium"
          >
            {loggingIn ? "Signing in…" : "Sign in"}
          </Button>
          {skipAuth && (
            <Button
              type="button"
              variant="outline"
              disabled={loggingIn}
              className="mt-2 h-8 w-full text-xs font-medium"
              onClick={async () => {
                try {
                  await loadUser();
                  show({ variant: "success", title: "Dev login", description: "Signed in as dev user." });
                  router.replace("/");
                } catch {
                  show({ variant: "error", title: "Dev login failed", description: "Could not load dev user." });
                }
              }}
            >
              Dev login (SKIP_AUTH)
            </Button>
          )}
        </form>
        <p className="mt-4 text-[11px] text-textSoft">
          Don&apos;t have an account?{" "}
          <Link href="/signup" className="text-primary hover:underline">
            Create one
          </Link>
          {" · "}
          First run? Demo: dev@localhost / dev
        </p>
      </Card>
    </div>
  );
}

