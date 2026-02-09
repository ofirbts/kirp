"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import React from "react";
import { cn } from "@/lib/utils";
import { useTenantContextStore } from "@/lib/stores/tenantContextStore";
import {
  LayoutDashboard,
  CheckCircle2,
  Brain,
  Bot,
  Clock3,
  Sparkles,
  Link2,
  Lightbulb,
  Share2,
  Bell,
} from "lucide-react";

type NavItem = {
  label: string;
  href: string;
  icon: React.ReactNode;
};

const NAV_ITEMS: NavItem[] = [
  {
    label: "Dashboard",
    href: "/dashboard",
    icon: <LayoutDashboard className="h-4 w-4" />,
  },
  {
    label: "Activity",
    href: "/notifications",
    icon: <Bell className="h-4 w-4" />,
  },
  {
    label: "Second Brain",
    href: "/second-brain",
    icon: <Sparkles className="h-4 w-4" />,
  },
  {
    label: "Graph",
    href: "/second-brain/graph",
    icon: <Share2 className="h-4 w-4" />,
  },
  {
    label: "Connections",
    href: "/connections",
    icon: <Link2 className="h-4 w-4" />,
  },
  {
    label: "Tasks",
    href: "/tasks",
    icon: <CheckCircle2 className="h-4 w-4" />,
  },
  {
    label: "Think",
    href: "/think",
    icon: <Brain className="h-4 w-4" />,
  },
  {
    label: "Insights",
    href: "/insights",
    icon: <Lightbulb className="h-4 w-4" />,
  },
  {
    label: "Agents",
    href: "/agents",
    icon: <Bot className="h-4 w-4" />,
  },
  {
    label: "History",
    href: "/history",
    icon: <Clock3 className="h-4 w-4" />,
  },
];

export const SideNav: React.FC = () => {
  const pathname = usePathname();
  const { tenantId, spaceId } = useTenantContextStore();

  return (
    <div
      className="flex h-full flex-col justify-between p-3"
      suppressHydrationWarning
    >
      <div className="space-y-4">
        <div
          className="flex items-center gap-3 px-2 pt-1"
          suppressHydrationWarning
        >
          <div className="flex h-9 w-9 items-center justify-center rounded-2xl bg-primary/20 text-primary shadow-soft" />
          <div className="flex flex-col" suppressHydrationWarning>
            <span className="text-sm font-semibold tracking-tight text-textMain">
              KIRP
            </span>
            <span className="text-[11px] text-textSoft">Intelligence OS</span>
          </div>
        </div>

        <nav className="space-y-1 text-sm" suppressHydrationWarning>
          {NAV_ITEMS.map((item) => {
            const isActive =
              pathname === item.href ||
              (item.href !== "/dashboard" && pathname.startsWith(item.href));

            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "flex items-center gap-3 rounded-xl px-3 py-2.5 text-textSoft transition-all hover:bg-surface2/70 hover:text-textMain",
                  isActive &&
                    "bg-surface2/90 text-textMain shadow-soft border border-[color:var(--color-border-strong)]"
                )}
              >
                <span
                  className={cn(
                    "flex h-7 w-7 items-center justify-center rounded-xl bg-surface2",
                    isActive && "bg-primary/15 text-primary"
                  )}
                >
                  {item.icon}
                </span>
                <span className="truncate font-medium">{item.label}</span>
              </Link>
            );
          })}
        </nav>
      </div>

      <div
        className="mt-4 rounded-xl bg-surface2/80 px-3 py-2 text-[11px] text-textSoft border border-[color:var(--color-border-subtle)]"
        suppressHydrationWarning
      >
        <div
          className="flex items-center justify-between gap-2"
          suppressHydrationWarning
        >
          <div className="flex flex-col" suppressHydrationWarning>
            <span className="text-[10px] uppercase tracking-wide text-textMuted">
              Scope
            </span>
            <span>
              tenant{" "}
              <span className="font-semibold text-textMain">
                {tenantId || "default"}
              </span>
            </span>
            <span>
              space{" "}
              <span className="font-semibold text-textMain">
                {spaceId || "all"}
              </span>
            </span>
          </div>
          <span className="rounded-full bg-primary/15 px-2 py-0.5 text-[10px] font-semibold text-primary">
            LIVE
          </span>
        </div>
      </div>
    </div>
  );
};
