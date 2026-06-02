"use client";

import React from "react";
import { usePathname, useRouter } from "next/navigation";
import { ChevronDown, LogOut, Moon, Sun, User } from "lucide-react";
import { NotificationBell } from "@/components/notifications/NotificationBell";
import { cn } from "@/lib/utils";
import { DEFAULT_TENANT_ID } from "@/lib/constants";
import { useTenantContextStore } from "@/lib/stores/tenantContextStore";
import { apiClient } from "@/lib/apiClient";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useToastStore } from "@/lib/stores/toastStore";
import { useAuthStore } from "@/lib/stores/authStore";
import { Breadcrumbs } from "@/components/navigation/Breadcrumbs";
import { BackButton } from "@/components/navigation/BackButton";
import { useTheme } from "next-themes";

type SectionMeta = {
  title: string;
  subtitle?: string;
  prefix: string;
};

const SECTIONS: SectionMeta[] = [
  { prefix: "/mission-control", title: "Mission Control", subtitle: "System health, ports, and activity." },
  { prefix: "/system-control", title: "System Control", subtitle: "Port scanner, Docker, and actions." },
  { prefix: "/dashboard", title: "Dashboard", subtitle: "System health, KPIs, and overview." },
  { prefix: "/notifications", title: "Activity Center", subtitle: "Notifications and activity." },
  { prefix: "/observability", title: "Observability", subtitle: "Health, metrics, and monitoring." },
  { prefix: "/traces", title: "Execution traces", subtitle: "Replay, drift, orchestration, governed runtime." },
  { prefix: "/agents", title: "Agents", subtitle: "Manage and inspect intelligence agents." },
  { prefix: "/tasks", title: "Tasks", subtitle: "Life-object tasks from ingest and Notion." },
  { prefix: "/insights", title: "Insights", subtitle: "Workload, patterns, commitments, and recommendations." },
  { prefix: "/second-brain/graph", title: "Life Graph", subtitle: "Knowledge graph of tasks, projects, commitments, events." },
  { prefix: "/events", title: "Events", subtitle: "Event stream and filters." },
  { prefix: "/decisions", title: "Decisions", subtitle: "Browse and explore decisions." },
  { prefix: "/graph", title: "Knowledge Graph", subtitle: "Explore entities and relationships." },
  { prefix: "/pipeline", title: "Pipeline", subtitle: "Orchestration flow and pipeline agents." },
  { prefix: "/content", title: "Content", subtitle: "Generated content intelligence." },
  { prefix: "/visuals", title: "Visuals", subtitle: "Generated visual prompts from runs." },
  { prefix: "/signals", title: "Signals", subtitle: "World context, trends, signals." },
  { prefix: "/run", title: "Run", subtitle: "Trigger Brand OS pipeline." },
  { prefix: "/history", title: "History", subtitle: "Human-readable timeline of your activity." },
  { prefix: "/governance/audit", title: "Audit & Compliance", subtitle: "Who did what, when." },
  { prefix: "/tenants", title: "Tenants", subtitle: "Tenant and space management." },
  { prefix: "/settings/users-roles", title: "Users & Roles", subtitle: "Directory and permissions." },
  { prefix: "/dev", title: "Dev Mode", subtitle: "API Explorer, Agent Debugger, Event Stream." },
];

function getSectionMeta(pathname: string): SectionMeta {
  const match =
    SECTIONS.find((s) => pathname.startsWith(s.prefix)) ??
    ({
      title: "Dashboard",
      subtitle: "System health and overview.",
      prefix: "/dashboard",
    } as SectionMeta);
  return match;
}

export const TopBar: React.FC = () => {
  const pathname = usePathname();
  const router = useRouter();
  const meta = getSectionMeta(pathname);
  const { tenantId, spaceId, setSpace } = useTenantContextStore();
  const { show } = useToastStore();
  const { theme, setTheme } = useTheme();

  const [tenants, setTenants] = React.useState<
    { id: string; name: string }[]
  >([]);
  const [spaces, setSpaces] = React.useState<{ id: string; name: string }[]>(
    [],
  );
  const [loadingTenants, setLoadingTenants] = React.useState(false);
  const [loadingSpaces, setLoadingSpaces] = React.useState(false);
  const { user, logout } = useAuthStore();

  // Load tenants on mount (display only). Root-level tenant is always "default"; do not overwrite from API.
  React.useEffect(() => {
    let cancelled = false;
    const loadTenants = async () => {
      setLoadingTenants(true);
      try {
        const res = await apiClient.listTenants();
        if (cancelled) return;
        const tenantsList = res.data ?? [];
        setTenants(tenantsList);
      } catch (err) {
        if (cancelled) return;
        const message =
          err instanceof Error ? err.message : "Failed to load tenants";
        show({
          variant: "error",
          title: "Tenant load failed",
          description: message,
        });
      } finally {
        if (!cancelled) {
          setLoadingTenants(false);
        }
      }
    };
    void loadTenants();
    return () => {
      cancelled = true;
    };
  }, [show]);

  // Load spaces for the fixed tenant.
  React.useEffect(() => {
    let cancelled = false;
    const loadSpaces = async () => {
      setLoadingSpaces(true);
      try {
        const res = await apiClient.listSpacesForTenant(tenantId ?? DEFAULT_TENANT_ID);
        if (cancelled) return;
        const spacesList = res.data ?? [];
        setSpaces(spacesList);
        // If current space is not valid under this tenant, default to first or clear.
        if (!spacesList.find((s) => s.id === spaceId)) {
          const nextSpaceId = spacesList[0]?.id;
          setSpace(nextSpaceId);
        }
      } catch (err) {
        if (cancelled) return;
        const message =
          err instanceof Error ? err.message : "Failed to load spaces";
        show({
          variant: "error",
          title: "Space load failed",
          description: message,
        });
        // On failure, clear spaces but keep existing selection.
        setSpaces([]);
      } finally {
        if (!cancelled) {
          setLoadingSpaces(false);
        }
      }
    };
    void loadSpaces();
    return () => {
      cancelled = true;
    };
  }, [tenantId, spaceId, setSpace, show]);

  return (
    <div className="flex h-14 w-full items-center justify-between gap-3" suppressHydrationWarning>
      {/* Left: back, breadcrumbs, section title + scope */}
      <div className="flex min-w-0 flex-1 items-center gap-3" suppressHydrationWarning>
        <div className="hidden sm:flex">
          <BackButton />
        </div>
        <div className="flex flex-col min-w-0" suppressHydrationWarning>
          <div className="flex items-center gap-2">
            <span className="truncate text-sm font-semibold text-textMain">
              {meta.title}
            </span>
          </div>
          <span className="text-xs text-textSoft truncate">
            {meta.subtitle ?? `KIRP / ${meta.title}`}
          </span>
          <Breadcrumbs className="mt-0.5" />
          <div className="mt-1 flex flex-wrap gap-1 text-[11px] text-textSoft">
            <span className="rounded-full bg-surface2 px-2 py-0.5 text-[10px] text-textMain">
              tenant {tenantId ?? DEFAULT_TENANT_ID}
            </span>
            <span className="rounded-full bg-surface2 px-2 py-0.5 text-[10px] text-textMain">
              space {spaceId || "all"}
            </span>
          </div>
        </div>

        {/* Tenant / Space selectors */}
        <div className="ml-4 flex items-center gap-2" suppressHydrationWarning>
          <Select
            value={tenantId ?? DEFAULT_TENANT_ID}
            onValueChange={() => {}}
            disabled
          >
            <SelectTrigger className="h-8 w-40 rounded-full border border-[color:var(--color-border-subtle)] bg-surface2 text-xs text-textMain hover:bg-surface3">
              <SelectValue
                placeholder={
                  loadingTenants ? "Loading tenants…" : "Select tenant"
                }
              />
            </SelectTrigger>
            <SelectContent className="border border-[color:var(--color-border-subtle)] bg-surface1 text-xs text-textMain">
              {tenants.map((t) => (
                <SelectItem key={t.id} value={t.id}>
                  {t.name ?? t.id}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          <Select
            value={spaceId ?? ""}
            onValueChange={(value) => {
              setSpace(value || null);
            }}
            disabled={loadingSpaces || spaces.length === 0}
          >
            <SelectTrigger className="h-8 w-36 rounded-full border border-[color:var(--color-border-subtle)] bg-surface2 text-xs text-textMain hover:bg-surface3">
              <SelectValue
                placeholder={
                  loadingSpaces
                    ? "Loading spaces…"
                    : spaces.length === 0
                      ? "No spaces"
                      : "Select space"
                }
              />
            </SelectTrigger>
            <SelectContent className="border border-[color:var(--color-border-subtle)] bg-surface1 text-xs text-textMain">
              {spaces.map((s) => (
                <SelectItem key={s.id} value={s.id}>
                  {s.name ?? s.id}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Right: alerts + user menu */}
      <div className="flex items-center gap-3 pl-2 md:pl-4" suppressHydrationWarning>
        <NotificationBell />

        {/* Theme toggle */}
        <button
          type="button"
          className="hidden md:inline-flex h-7 w-7 items-center justify-center rounded-full border border-[color:var(--color-border-subtle)] bg-surface2 text-xs text-textSoft hover:border-primary/60 hover:text-primary"
          onClick={() => setTheme(theme === "light" ? "dark" : "light")}
          aria-label="Toggle theme"
        >
          {theme === "light" ? (
            <Moon className="h-3.5 w-3.5" />
          ) : (
            <Sun className="h-3.5 w-3.5" />
          )}
        </button>

        {user ? (
          <button
            type="button"
            className="hidden md:flex items-center gap-2 rounded-full border border-[color:var(--color-border-subtle)] bg-surface2 px-2 py-1 text-xs text-textMain hover:border-primary/60 hover:text-primary"
            onClick={() => {
              logout();
              router.push("/logout");
            }}
          >
            <span className="inline-flex h-6 w-6 items-center justify-center rounded-full bg-surface3">
              <User className="h-3.5 w-3.5" />
            </span>
            <span className="max-w-[120px] truncate">
              {user.email}
            </span>
            <LogOut className="h-3 w-3" />
          </button>
        ) : (
          <button
            type="button"
            className="hidden md:flex items-center gap-2 rounded-full border border-primary/70 bg-surface2 px-3 py-1 text-xs text-primary hover:bg-surface3"
            onClick={() => router.push("/login")}
          >
            <User className="h-3.5 w-3.5" />
            <span className="max-w-[120px] truncate">Sign in</span>
          </button>
        )}
      </div>
    </div>
  );
};

