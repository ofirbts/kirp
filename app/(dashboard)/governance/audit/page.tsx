"use client";

import React, { useEffect, useState, useCallback, Suspense } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { DataTable } from "@/components/dashboard/DataTable";
import { PageSkeleton } from "@/components/dashboard/PageSkeleton";
import { ErrorState } from "@/components/feedback/ErrorState";
import { apiClient } from "@/lib/apiClient";
import type { AuditEntry } from "@/lib/types";

function AuditContent() {
  const [entries, setEntries] = useState<AuditEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedEntry, setSelectedEntry] = useState<AuditEntry | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiClient.listAuditEntries();
      setEntries(res.data ?? []);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load audit entries");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const successCount = entries.filter((e) => e.result === "success").length;
  const failureCount = entries.filter((e) => e.result === "failure").length;

  if (loading && entries.length === 0) {
    return <PageSkeleton title subtitle tableRows={8} />;
  }

  return (
    <div className="space-y-6" suppressHydrationWarning>
      <div suppressHydrationWarning>
        <h1 className="text-2xl font-bold tracking-tight">Audit & Compliance</h1>
        <p className="text-muted-foreground text-sm mt-1">
          Who did what, when, on what.
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Card className="border-neutral-800 bg-neutral-900/70">
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Compliance summary</CardTitle>
          </CardHeader>
          <CardContent className="text-sm">
            <p className="text-neutral-400">
              Total entries: <span className="font-medium text-neutral-200">{entries.length}</span>
            </p>
            <p className="mt-1 text-neutral-400">
              Success: <span className="font-medium text-emerald-400">{successCount}</span>
              {" · "}
              Failure: <span className="font-medium text-red-400">{failureCount}</span>
            </p>
          </CardContent>
        </Card>
      </div>

      {error && <ErrorState message={error} onRetry={load} />}

      <DataTable<AuditEntry>
        title="Audit entries"
        data={entries}
        keyExtractor={(r) => r.id}
        loading={loading}
        error={error}
        onRetry={load}
        columns={[
          { key: "action", header: "Action", render: (r) => r.action },
          { key: "actorType", header: "Actor", render: (r) => `${r.actorType}:${r.actorId}` },
          { key: "resourceType", header: "Resource", render: (r) => r.resourceType },
          { key: "result", header: "Result", render: (r) => r.result },
          { key: "timestamp", header: "Time", render: (r) => r.timestamp?.slice(0, 19) ?? "—" },
        ]}
        emptyMessage="No audit entries."
        pageSize={10}
        onRowClick={(row) => {
          setSelectedEntry(row);
          setDrawerOpen(true);
        }}
      />

      <Sheet open={drawerOpen} onOpenChange={setDrawerOpen}>
        <SheetContent side="right" className="w-full max-w-md border-neutral-800 bg-neutral-950">
          <SheetHeader>
            <SheetTitle className="text-sm font-semibold text-neutral-100">
              Audit entry
            </SheetTitle>
          </SheetHeader>
          {selectedEntry && (
            <div className="mt-4 space-y-4 text-sm">
              <div>
                <p className="text-xs font-medium text-neutral-500">ID</p>
                <p className="font-mono text-xs text-neutral-300">{selectedEntry.id}</p>
              </div>
              <div>
                <p className="text-xs font-medium text-neutral-500">Action / Result</p>
                <p className="text-neutral-200">{selectedEntry.action} · {selectedEntry.result}</p>
              </div>
              <div>
                <p className="text-xs font-medium text-neutral-500">Actor</p>
                <p className="text-neutral-300">{selectedEntry.actorType}:{selectedEntry.actorId}</p>
              </div>
              <div>
                <p className="text-xs font-medium text-neutral-500">Resource</p>
                <p className="text-neutral-300">{selectedEntry.resourceType}{selectedEntry.resourceId ? ` · ${selectedEntry.resourceId}` : ""}</p>
              </div>
              <div>
                <p className="text-xs font-medium text-neutral-500">Timestamp</p>
                <p className="text-neutral-300">{selectedEntry.timestamp}</p>
              </div>
              <div>
                <p className="text-xs font-medium text-neutral-500">Metadata</p>
                <pre className="max-h-32 overflow-auto rounded bg-neutral-900 p-2 text-xs text-neutral-400">
                  {JSON.stringify(selectedEntry.metadata ?? {}, null, 2)}
                </pre>
              </div>
            </div>
          )}
        </SheetContent>
      </Sheet>
    </div>
  );
}

export default function GovernanceAuditPage() {
  return (
    <Suspense fallback={<PageSkeleton title subtitle tableRows={8} />}>
      <AuditContent />
    </Suspense>
  );
}
