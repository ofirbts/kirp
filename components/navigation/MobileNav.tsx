"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { LayoutDashboard, CheckCircle2, History, Bell, Target } from "lucide-react";
import { cn } from "@/lib/utils";

const ITEMS = [
  { href: "/dashboard", label: "Home", icon: LayoutDashboard },
  { href: "/tasks", label: "Tasks", icon: CheckCircle2 },
  { href: "/m3", label: "Identity", icon: Target },
  { href: "/history", label: "History", icon: History },
  { href: "/notifications", label: "Activity", icon: Bell },
];

export function MobileNav() {
  const pathname = usePathname();
  return (
    <nav className="fixed inset-x-0 bottom-3 z-40 px-4 md:hidden">
      <div className="mx-auto max-w-md rounded-2xl bg-surface1/95 border border-[color:var(--color-border-subtle)] shadow-soft backdrop-blur-xl">
        <div className="flex items-center justify-around py-1.5">
          {ITEMS.map((item) => {
            const isActive =
              pathname === item.href ||
              (item.href !== "/dashboard" && pathname.startsWith(item.href));
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "flex flex-col items-center gap-0.5 px-2 py-1 text-[11px]",
                  isActive ? "text-primary" : "text-textSoft hover:text-textMain",
                )}
              >
                <span
                  className={cn(
                    "flex h-7 w-7 items-center justify-center rounded-xl bg-surface2",
                    isActive && "bg-primary/15 text-primary",
                  )}
                >
                  <Icon className="h-3.5 w-3.5" />
                </span>
                <span className="leading-none">{item.label}</span>
              </Link>
            );
          })}
        </div>
      </div>
    </nav>
  );
}

