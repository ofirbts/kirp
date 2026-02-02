"use client";

import React from "react";
import { usePathname, useRouter } from "next/navigation";
import { Bell, ChevronDown, User } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
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

type SectionMeta = {
  title: string;
  subtitle?: string;
  prefix: string;
};

const SECTIONS: SectionMeta[] = [
  { prefix: "/mission-control", title: "Mission Control", subtitle: "System health, ports, and activity." },
  { prefix: "/system-control", title: "System Control", subtitle: "Port scanner, Docker, and actions." },
  { prefix: "/dashboard", title: "Dashboard", subtitle: "System health, KPIs, and overview." },
  { prefix: "/observability", title: "Observability", subtitle: "Health, metrics, and monitoring." },
  { prefix: "/agents", title: "Agents", subtitle: "Manage and inspect intelligence agents." },
  { prefix: "/events", title: "Events", subtitle: "Event stream and filters." },
  { prefix: "/decisions", title: "Decisions", subtitle: "Browse and explore decisions." },
  { prefix: "/graph", title: "Knowledge Graph", subtitle: "Explore entities and relationships." },
  { prefix: "/pipeline", title: "Pipeline", subtitle: "Orchestration flow and pipeline agents." },
  { prefix: "/content", title: "Content", subtitle: "Generated content intelligence." },
  { prefix: "/visuals", title: "Visuals", subtitle: "Generated visual prompts from runs." },
  { prefix: "/signals", title: "Signals", subtitle: "World context, trends, signals." },
  { prefix: "/run", title: "Run", subtitle: "Trigger Brand OS pipeline." },
  { prefix: "/history", title: "History", subtitle: "Past runs from Content Memory Log." },
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
  const { tenantId, spaceId, setTenant, setSpace } = useTenantContextStore();
  const { show } = useToastStore();

  const [tenants, setTenants] = React.useState<
    { id: string; name: string }[]
  >([]);
  const [spaces, setSpaces] = React.useState<{ id: string; name: string }[]>(
    [],
  );
  const [loadingTenants, setLoadingTenants] = React.useState(false);
  const [loadingSpaces, setLoadingSpaces] = React.useState(false);
  const [notificationsCount, setNotificationsCount] = React.useState(0);
  const { user, logout } = useAuthStore();

  React.useEffect(() => {
    let cancelled = false;
    apiClient.getStats().then((s) => {
      if (cancelled) return;
      const n = typeof (s as Record<string, unknown>)?.notifications === "number"
        ? (s as Record<string, number>).notifications
        : 0;
      setNotificationsCount(Math.min(99, Math.max(0, n)));
    }).catch(() => { });
    return () => { cancelled = true; };
  }, [tenantId]);

  // Load tenants on mount.
  React.useEffect(() => {
    let cancelled = false;
    const loadTenants = async () => {
      setLoadingTenants(true);
      try {
        const res = await apiClient.listTenants();
        if (cancelled) return;
        const tenantsList = res.data ?? [];
        setTenants(tenantsList);
        // If current tenant is not in the list, default to the first tenant.
        if (!tenantsList.find((t) => t.id === tenantId) && tenantsList.length > 0) {
          setTenant(tenantsList[0].id);
        } else if (tenantsList.length === 0 && !tenantId) {
          setTenant("default");
        }
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
  }, [setTenant, show, tenantId]);

  // Load spaces whenever tenant changes.
  React.useEffect(() => {
    let cancelled = false;
    const loadSpaces = async () => {
      if (!tenantId) return;
      setLoadingSpaces(true);
      try {
        const res = await apiClient.listSpacesForTenant(tenantId);
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
  }, [tenantId]);

  return (
    <header className="flex h-14 flex-shrink-0 items-center border-b border-neutral-800 bg-neutral-950/80 px-4 backdrop-blur" suppressHydrationWarning>
      {/* Left: section title + breadcrumbs placeholder */}
      <div className="flex min-w-0 flex-1 items-center gap-3" suppressHydrationWarning>
        <div className="flex flex-col" suppressHydrationWarning>
          <span className="truncate text-sm font-semibold text-neutral-100">
            {meta.title}
          </span>
          <span className="text-xs text-neutral-500">
            {meta.subtitle ?? `KIRP / ${meta.title}`}
          </span>
          <span className="mt-0.5 text-[11px] text-neutral-500">
            Scope:{" "}
            <span className="rounded-full bg-neutral-900 px-2 py-0.5 text-[10px] text-neutral-200">
              tenant {tenantId || "not set"}
            </span>
            <span className="ml-1 rounded-full bg-neutral-900 px-2 py-0.5 text-[10px] text-neutral-200">
              space {spaceId || "all"}
            </span>
          </span>
        </div>

        {/* Tenant / Space selectors */}
        <div className="ml-4 flex items-center gap-2" suppressHydrationWarning>
          <Select
            value={tenantId ?? ""}
            onValueChange={(value) => {
              setTenant(value || undefined);
            }}
            disabled={loadingTenants || tenants.length === 0}
          >
            <SelectTrigger
              className={cn(
                "h-8 w-44 border-neutral-700 bg-neutral-900 text-xs text-neutral-200 hover:bg-neutral-800",
              )}
            >
              <SelectValue
                placeholder={
                  loadingTenants ? "Loading tenants…" : "Select tenant"
                }
              />
            </SelectTrigger>
            <SelectContent className="border-neutral-700 bg-neutral-950 text-xs text-neutral-100">
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
              const next = value || undefined;
              setSpace(next);
            }}
            disabled={loadingSpaces || spaces.length === 0}
          >
            <SelectTrigger className="h-8 w-40 border-neutral-700 bg-neutral-900 text-xs text-neutral-200 hover:bg-neutral-800">
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
            <SelectContent className="border-neutral-700 bg-neutral-950 text-xs text-neutral-100">
              {spaces.map((s) => (
                <SelectItem key={s.id} value={s.id}>
                  {s.name ?? s.id}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Right: alerts + user menu placeholders */}
      <div className="flex items-center gap-3 pl-4" suppressHydrationWarning>
        <button
          type="button"
          className="relative inline-flex h-8 w-8 items-center justify-center rounded-full border border-neutral-700 bg-neutral-900 text-neutral-300 hover:border-cyan-500 hover:text-cyan-400"
        >
          <Bell className="h-4 w-4" />
          {notificationsCount > 0 && (
            <span className="absolute -right-0.5 -top-0.5 inline-flex h-3 w-3 items-center justify-center rounded-full bg-red-500 text-[9px] font-semibold text-white">
              {notificationsCount > 99 ? "99" : notificationsCount}
            </span>
          )}
        </button>

        {user ? (
          <button
            type="button"
            className="flex items-center gap-2 rounded-full border border-neutral-700 bg-neutral-900 px-2 py-1 text-xs text-neutral-200 hover:border-cyan-500 hover:text-cyan-300"
            onClick={() => {
              logout();
              router.push("/login");
            }}
          >
            <span className="inline-flex h-6 w-6 items-center justify-center rounded-full bg-neutral-800">
              <User className="h-3.5 w-3.5" />
            </span>
            <span className="max-w-[120px] truncate">
              {user.email}
            </span>
            <ChevronDown className="h-3 w-3" />
          </button>
        ) : (
          <button
            type="button"
            className="flex items-center gap-2 rounded-full border border-cyan-600 bg-neutral-900 px-3 py-1 text-xs text-cyan-300 hover:bg-neutral-800"
            onClick={() => router.push("/login")}
          >
            <User className="h-3.5 w-3.5" />
            <span className="max-w-[120px] truncate">Sign in</span>
          </button>
        )}
      </div>
    </header>
  );
};

