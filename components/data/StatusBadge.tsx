"use client";

import React from "react";
import { cn } from "@/lib/utils";

type StatusBadgeProps = {
  status: string;
  size?: "sm" | "md";
  className?: string;
};

function getStatusClasses(status: string): string {
  const s = status.toLowerCase();

  if (["healthy", "success", "running", "active"].includes(s)) {
    return "bg-emerald-900/40 text-emerald-300 border-emerald-700/70";
  }
  if (["degraded", "warning", "queued", "pending"].includes(s)) {
    return "bg-amber-900/40 text-amber-300 border-amber-700/70";
  }
  if (["down", "error", "failed", "critical"].includes(s)) {
    return "bg-red-900/40 text-red-300 border-red-700/70";
  }
  if (["paused"].includes(s)) {
    return "bg-neutral-800 text-neutral-300 border-neutral-600";
  }
  return "bg-neutral-900 text-neutral-300 border-neutral-700/70";
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({
  status,
  size = "sm",
  className,
}) => {
  const base =
    "inline-flex items-center rounded-full border px-2 font-medium uppercase tracking-wide";
  const sizeClasses = size === "sm" ? "h-5 text-[10px]" : "h-6 text-xs";

  return (
    <span className={cn(base, sizeClasses, getStatusClasses(status), className)}>
      {status}
    </span>
  );
};

