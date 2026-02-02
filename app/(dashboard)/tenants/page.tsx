"use client";

import React, { useEffect, useState, useCallback, Suspense } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { DataTable } from "@/components/dashboard/DataTable";
import { PageSkeleton } from "@/components/dashboard/PageSkeleton";
import { ErrorState } from "@/components/feedback/ErrorState";
import { apiClient } from "@/lib/apiClient";
import type { Tenant, Space } from "@/lib/types";

function TenantsContent() {
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [spacesByTenant, setSpacesByTenant] = useState<Record<string, Space[]>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedTenant, setSelectedTenant] = useState<Tenant | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiClient.listTenants();
      const list = res.data ?? [];
      setTenants(list);
      const spaces: Record<string, Space[]> = {};
      for (const t of list) {
        try {
          const spRes = await apiClient.listSpacesForTenant(t.id);
          spaces[t.id] = spRes.data ?? [];
        } catch {
          spaces[t.id] = [];
        }
      }
      setSpacesByTenant(spaces);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load tenants");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  if (loading && tenants.length === 0) {
    return <PageSkeleton title subtitle tableRows={8} />;
  }

  return (
    <div className="space-y-6" suppressHydrationWarning>
      <div suppressHydrationWarning>
        <h1 className="text-2xl font-bold tracking-tight">Tenants</h1>
        <p className="text-muted-foreground text-sm mt-1">Tenant and space management.</p>
      </div>
      {error && <ErrorState message={error} onRetry={load} />}
      <DataTable<Tenant>
        title="Tenants"
        data={tenants}
        keyExtractor={(r) => r.id}
        loading={loading}
        error={error}
        onRetry={load}
        columns={[
          { key: "name", header: "Name", render: (r) => r.name },
          { key: "slug", header: "Slug", render: (r) => r.slug },
          { key: "id", header: "ID", render: (r) => r.id.slice(0, 8) + "…" },
        ]}
        emptyMessage="No tenants."
        pageSize={10}
        onRowClick={(row) => {
          setSelectedTenant(row);
          setDrawerOpen(true);
        }}
      />
      <Card className="border-neutral-800 bg-neutral-900/70">
        <CardHeader>
          <CardTitle className="text-base">Spaces by tenant</CardTitle>
        </CardHeader>
        <CardContent>
          {tenants.length === 0 ? (
            <p className="text-sm text-neutral-500">No tenants.</p>
          ) : (
            <ul className="space-y-3 text-sm">
              {tenants.map((t) => (
                <li key={t.id}>
                  <span className="font-medium text-neutral-200">{t.name}</span>
                  <ul className="mt-1 ml-4 list-disc text-neutral-400">
                    {(spacesByTenant[t.id] ?? []).map((s) => (
                      <li key={s.id}>{s.name} ({s.slug})</li>
                    ))}
                    {(spacesByTenant[t.id] ?? []).length === 0 && (
                      <li className="text-neutral-500">No spaces</li>
                    )}
                  </ul>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
      <Sheet open={drawerOpen} onOpenChange={setDrawerOpen}>
        <SheetContent side="right" className="w-full max-w-md border-neutral-800 bg-neutral-950">
          <SheetHeader>
            <SheetTitle className="text-sm font-semibold text-neutral-100">Tenant details</SheetTitle>
          </SheetHeader>
          {selectedTenant && (
            <div className="mt-4 space-y-4 text-sm">
              <div>
                <p className="text-xs font-medium text-neutral-500">ID</p>
                <p className="font-mono text-xs text-neutral-300">{selectedTenant.id}</p>
              </div>
              <div>
                <p className="text-xs font-medium text-neutral-500">Name / Slug</p>
                <p className="text-neutral-200">{selectedTenant.name} · {selectedTenant.slug}</p>
              </div>
              <div>
                <p className="text-xs font-medium text-neutral-500">Spaces</p>
                <ul className="mt-1 space-y-1 text-neutral-400">
                  {(spacesByTenant[selectedTenant.id] ?? []).map((s) => (
                    <li key={s.id}>{s.name} ({s.slug})</li>
                  ))}
                  {(spacesByTenant[selectedTenant.id] ?? []).length === 0 && (
                    <li className="text-neutral-500">No spaces</li>
                  )}
                </ul>
              </div>
            </div>
          )}
        </SheetContent>
      </Sheet>
    </div>
  );
}

export default function TenantsPage() {
  return (
    <Suspense fallback={<PageSkeleton title subtitle tableRows={8} />}>
      <TenantsContent />
    </Suspense>
  );
}
