"use client";

import React from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { useAuthStore } from "@/lib/stores/authStore";
import { useToastStore } from "@/lib/stores/toastStore";

export default function SignupPage() {
  const router = useRouter();
  const { signup, loggingIn } = useAuthStore();
  const { show } = useToastStore();

  const [email, setEmail] = React.useState("");
  const [name, setName] = React.useState("");
  const [password, setPassword] = React.useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim() || !password.trim() || !name.trim()) {
      show({
        variant: "warning",
        title: "Missing information",
        description: "Please fill in name, email, and password.",
      });
      return;
    }
    try {
      await signup(email.trim(), password.trim(), name.trim());
      show({
        variant: "success",
        title: "Account created",
        description: "Welcome to KIRP.",
      });
      router.push("/");
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Signup failed. Please try again.";
      show({
        variant: "error",
        title: "Signup failed",
        description: message,
      });
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-bg px-4">
      <Card className="w-full max-w-sm border-[color:var(--color-border-subtle)] bg-surface1 px-5 py-6 text-sm shadow-soft">
        <h1 className="text-base font-semibold text-textMain">
          Create your KIRP account
        </h1>
        <p className="mt-1 text-xs text-textSoft">
          We&apos;ll create a personal tenant and default space for you.
        </p>
        <form onSubmit={handleSubmit} className="mt-4 space-y-3">
          <div>
            <label className="block text-xs font-medium text-textMain">
              Name
            </label>
            <Input
              type="text"
              autoComplete="name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="mt-1 h-8 border-[color:var(--color-border-subtle)] bg-surface2 text-xs text-textMain placeholder:text-textSoft"
              placeholder="Your name"
            />
          </div>
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
              placeholder="you@example.com"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-textMain">
              Password
            </label>
            <Input
              type="password"
              autoComplete="new-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="mt-1 h-8 border-[color:var(--color-border-subtle)] bg-surface2 text-xs text-textMain placeholder:text-textSoft"
              placeholder="At least 8 characters"
            />
          </div>
          <Button
            type="submit"
            disabled={loggingIn}
            className="mt-2 h-8 w-full text-xs font-medium"
          >
            {loggingIn ? "Creating..." : "Sign up"}
          </Button>
        </form>
        <p className="mt-4 text-[11px] text-textSoft">
          Already have an account?{" "}
          <Link href="/login" className="text-primary hover:underline">
            Sign in
          </Link>
        </p>
      </Card>
    </div>
  );
}

