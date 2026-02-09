"use client";

import React from "react";
import { useRouter, usePathname } from "next/navigation";
import { ArrowLeft } from "lucide-react";
import { cn } from "@/lib/utils";

const ROOT_PATHS = new Set([
  "/",
  "/dashboard",
  "/mission-control",
  "/system-control",
  "/tasks",
  "/agents",
  "/graph",
  "/second-brain",
  "/history",
  "/notifications",
  "/connections",
  "/insights",
]);

export function BackButton({ className }: { className?: string }) {
  const router = useRouter();
  const pathname = usePathname();

  if (!pathname || ROOT_PATHS.has(pathname)) return null;

  const segments = pathname.split("?")[0].split("#")[0].split("/").filter(Boolean);
  if (segments.length <= 1) return null;

  const parentPath = "/" + segments.slice(0, -1).join("/");

  const handleClick = () => {
    if (parentPath && parentPath !== pathname) {
      router.push(parentPath);
    } else {
      router.back();
    }
  };

  return (
    <button
      type="button"
      onClick={handleClick}
      className={cn(
        "inline-flex h-7 w-7 items-center justify-center rounded-full border border-[color:var(--color-border-subtle)] bg-surface2 text-xs text-textSoft hover:border-primary/60 hover:text-primary",
        className,
      )}
      aria-label="Go back"
    >
      <ArrowLeft className="h-3 w-3" />
    </button>
  );
}

