"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";

type Crumb = { href: string; label: string };

const LABEL_MAP: Record<string, string> = {
  dashboard: "Dashboard",
  "mission-control": "Mission Control",
  "system-control": "System Control",
  connections: "Connections",
  tasks: "Tasks",
  insights: "Insights",
  agents: "Agents",
  history: "History",
  notifications: "Activity Center",
  graph: "Graph",
  events: "Events",
  decisions: "Decisions",
  "second-brain": "Second Brain",
};

function buildCrumbs(pathname: string): Crumb[] {
  const clean = pathname.split("?")[0].split("#")[0];
  const segments = clean.split("/").filter(Boolean);
  if (segments.length === 0) return [{ href: "/dashboard", label: "Dashboard" }];
  const crumbs: Crumb[] = [];
  let acc = "";
  for (const seg of segments) {
    acc += "/" + seg;
    const label =
      LABEL_MAP[seg] ??
      seg
        .replace(/-/g, " ")
        .replace(/\b\w/g, (c) => c.toUpperCase());
    crumbs.push({ href: acc || "/", label });
  }
  return crumbs;
}

export function Breadcrumbs({ className }: { className?: string }) {
  const pathname = usePathname();
  const crumbs = buildCrumbs(pathname);
  if (!crumbs.length) return null;

  return (
    <nav
      aria-label="Breadcrumb"
      className={cn("flex items-center gap-1 text-[11px] text-textSoft", className)}
    >
      {crumbs.map((crumb, idx) => {
        const isLast = idx === crumbs.length - 1;
        return (
          <span key={crumb.href} className="inline-flex items-center gap-1">
            {idx > 0 && <ChevronRight className="h-3 w-3 opacity-60" />}
            {isLast ? (
              <span className="truncate max-w-[140px]" aria-current="page">
                {crumb.label}
              </span>
            ) : (
              <Link
                href={crumb.href}
                className="truncate max-w-[120px] hover:text-textMain"
              >
                {crumb.label}
              </Link>
            )}
          </span>
        );
      })}
    </nav>
  );
}