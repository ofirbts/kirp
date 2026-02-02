"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import React from "react";
import { cn } from "@/lib/utils";
import { useTenantContextStore } from "@/lib/stores/tenantContextStore";

type NavItem = {
  label: string;
  href: string;
  icon?: React.ReactNode;
};

type NavSection = {
  label: string;
  items: NavItem[];
};

const SECTIONS: NavSection[] = [
  {
    label: "Control",
    items: [
      { label: "Mission Control", href: "/mission-control" },
      { label: "System Control", href: "/system-control" },
    ],
  },
  {
    label: "Main",
    items: [
      { label: "Dashboard", href: "/dashboard" },
      { label: "Observability", href: "/observability" },
    ],
  },
  {
    label: "Intelligence",
    items: [
      { label: "Agents", href: "/agents" },
      { label: "Events", href: "/events" },
      { label: "Decisions", href: "/decisions" },
      { label: "Knowledge Graph", href: "/graph" },
    ],
  },
  {
    label: "Pipeline & Content",
    items: [
      { label: "Pipeline", href: "/pipeline" },
      { label: "Content", href: "/content" },
      { label: "Visuals", href: "/visuals" },
      { label: "Signals", href: "/signals" },
      { label: "Run", href: "/run" },
      { label: "History", href: "/history" },
    ],
  },
  {
    label: "Governance",
    items: [{ label: "Audit", href: "/governance/audit" }],
  },
  {
    label: "Settings",
    items: [
      { label: "Tenants", href: "/tenants" },
      { label: "Users & Roles", href: "/settings/users-roles" },
    ],
  },
  {
    label: "Dev",
    items: [{ label: "Dev Mode", href: "/dev" }],
  },
];

export const SideNav: React.FC = () => {
  const pathname = usePathname();
  const { tenantId, spaceId } = useTenantContextStore();

  return (
    <aside
      className="hidden h-full w-64 flex-shrink-0 border-r border-neutral-800 bg-neutral-950/95 md:flex md:flex-col"
      suppressHydrationWarning
    >
      <div className="flex items-center gap-2 px-4 py-4" suppressHydrationWarning>
        <div className="h-8 w-8 rounded-lg bg-cyan-500/90" suppressHydrationWarning />
        <div className="flex flex-col" suppressHydrationWarning>
          <span className="text-sm font-semibold tracking-tight text-neutral-50">
            KIRP
          </span>
          <span className="text-xs text-neutral-400">Intelligence OS</span>
        </div>
      </div>

      <nav className="flex-1 overflow-y-auto px-2 pb-4 pt-2 text-sm">
        {SECTIONS.map((section) => (
          <div key={section.label} className="mb-4" suppressHydrationWarning>
            <div
              className="px-3 pb-1 pt-2 text-xs font-medium uppercase tracking-wide text-neutral-500"
              suppressHydrationWarning
            >
              {section.label}
            </div>
            <ul className="space-y-1">
              {section.items.map((item) => {
                const isActive =
                  pathname === item.href ||
                  (item.href !== "/dashboard" &&
                    item.href !== "/mission-control" &&
                    item.href !== "/system-control" &&
                    pathname.startsWith(item.href));

                return (
                  <li key={item.href}>
                    <Link
                      href={item.href}
                      className={cn(
                        "flex items-center gap-2 rounded-md px-3 py-2 text-neutral-300 transition-colors hover:bg-neutral-800 hover:text-neutral-50",
                        isActive &&
                        "bg-neutral-800 text-neutral-50 shadow-sm shadow-cyan-500/30"
                      )}
                    >
                      {item.icon}
                      <span className="truncate">{item.label}</span>
                    </Link>
                  </li>
                );
              })}
            </ul>
          </div>
        ))}
      </nav>

      <div
        className="border-t border-neutral-800 px-4 py-3 text-xs text-neutral-500"
        suppressHydrationWarning
      >
        <div className="flex items-center justify-between gap-2" suppressHydrationWarning>
          <div className="flex flex-col" suppressHydrationWarning>
            <span>env: dev</span>
            <span className="text-[10px] text-neutral-500">
              tenant:{" "}
              <span className="font-medium text-neutral-300">
                {tenantId || "not set"}
              </span>
              {" · "}
              space:{" "}
              <span className="font-medium text-neutral-300">
                {spaceId || "all"}
              </span>
            </span>
          </div>
          <span className="rounded-full bg-neutral-900 px-2 py-0.5 text-[10px] text-cyan-400">
            SCOPE
          </span>
        </div>
      </div>
    </aside>
  );
};
