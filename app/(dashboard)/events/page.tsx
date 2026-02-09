"use client";

import React, { useEffect, useState, useCallback, Suspense } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { DataTable } from "@/components/dashboard/DataTable";
import { PageSkeleton } from "@/components/dashboard/PageSkeleton";
import { ErrorState } from "@/components/feedback/ErrorState";
import { apiClient } from "@/lib/apiClient";
import { DEFAULT_TENANT_ID } from "@/lib/constants";
import { useTenantContextStore } from "@/lib/stores/tenantContextStore";
import type { Event, EventSeverity } from "@/lib/types";

function EventsContent() {
  const { tenantId, spaceId } = useTenantContextStore();
  const [events, setEvents] = useState<Event[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [topic, setTopic] = useState("");
  const [severity, setSeverity] = useState<string>("");
  const [status, setStatus] = useState<string>("");
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [selectedEvent, setSelectedEvent] = useState<Event | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiClient.listEvents({
        tenantId: tenantId ?? DEFAULT_TENANT_ID,
        spaceId: spaceId ?? "all",
        topic: topic || undefined,
        severity: (severity as EventSeverity) || undefined,
        status: status || undefined,
        from: from || undefined,
        to: to || undefined,
      });
      setEvents(res.data ?? []);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load events");
    } finally {
      setLoading(false);
    }
  }, [tenantId, spaceId, topic, severity, status, from, to]);

  useEffect(() => {
    load();
  }, [load]);

  if (loading && events.length === 0) {
    return <PageSkeleton title subtitle tableRows={8} />;
  }

  return (
    <div className="space-y-6" suppressHydrationWarning>
      <div suppressHydrationWarning>
        <h1 className="text-2xl font-bold tracking-tight">Events</h1>
        <p className="text-muted-foreground text-sm mt-1">
          Event stream and filters.
        </p>
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          load();
        }}
        className="flex flex-wrap items-center gap-3"
      >
        <Input
          placeholder="Topic"
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
          className="h-8 w-40 border-neutral-700 bg-neutral-900 text-sm"
        />
        <Select value={severity || "all"} onValueChange={(v) => setSeverity(v === "all" ? "" : v)}>
          <SelectTrigger className="w-[130px] border-neutral-700 bg-neutral-900">
            <SelectValue placeholder="Severity" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All</SelectItem>
            <SelectItem value="debug">Debug</SelectItem>
            <SelectItem value="info">Info</SelectItem>
            <SelectItem value="warning">Warning</SelectItem>
            <SelectItem value="error">Error</SelectItem>
            <SelectItem value="critical">Critical</SelectItem>
          </SelectContent>
        </Select>
        <Select value={status || "all"} onValueChange={(v) => setStatus(v === "all" ? "" : v)}>
          <SelectTrigger className="w-[130px] border-neutral-700 bg-neutral-900">
            <SelectValue placeholder="Status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All</SelectItem>
            <SelectItem value="processed">Processed</SelectItem>
            <SelectItem value="pending">Pending</SelectItem>
            <SelectItem value="failed">Failed</SelectItem>
          </SelectContent>
        </Select>
        <Input
          type="datetime-local"
          placeholder="From"
          value={from}
          onChange={(e) => setFrom(e.target.value)}
          className="h-8 w-44 border-neutral-700 bg-neutral-900 text-sm"
        />
        <Input
          type="datetime-local"
          placeholder="To"
          value={to}
          onChange={(e) => setTo(e.target.value)}
          className="h-8 w-44 border-neutral-700 bg-neutral-900 text-sm"
        />
        <Button type="submit" variant="outline" size="sm" disabled={loading}>
          {loading ? "Loading…" : "Apply"}
        </Button>
      </form>

      {error && <ErrorState message={error} onRetry={load} />}

      <DataTable<Event>
        title="Events"
        data={events}
        keyExtractor={(r) => r.id}
        loading={loading}
        error={error}
        onRetry={load}
        columns={[
          { key: "topic", header: "Topic", render: (r) => r.topic || "—" },
          { key: "severity", header: "Severity", render: (r) => r.severity },
          { key: "timestamp", header: "Time", render: (r) => r.timestamp?.slice(0, 19) ?? "—" },
          { key: "payloadPreview", header: "Preview", render: (r) => (r.payloadPreview ?? "").slice(0, 40) },
        ]}
        emptyMessage="No events match the filters."
        pageSize={10}
        onRowClick={(row) => {
          setSelectedEvent(row);
          setDrawerOpen(true);
        }}
      />

      <Sheet open={drawerOpen} onOpenChange={setDrawerOpen}>
        <SheetContent side="right" className="w-full max-w-md border-neutral-800 bg-neutral-950">
          <SheetHeader>
            <SheetTitle className="text-sm font-semibold text-neutral-100">
              Event details
            </SheetTitle>
          </SheetHeader>
          {selectedEvent && (
            <div className="mt-4 space-y-4 text-sm">
              <div>
                <p className="text-xs font-medium text-neutral-500">ID</p>
                <p className="font-mono text-xs text-neutral-300">{selectedEvent.id}</p>
              </div>
              <div>
                <p className="text-xs font-medium text-neutral-500">Topic / Severity</p>
                <p className="text-neutral-200">{selectedEvent.topic} · {selectedEvent.severity}</p>
              </div>
              <div>
                <p className="text-xs font-medium text-neutral-500">Timestamp</p>
                <p className="text-neutral-300">{selectedEvent.timestamp}</p>
              </div>
              <div>
                <p className="text-xs font-medium text-neutral-500">Payload preview</p>
                <p className="text-neutral-400 break-all">{selectedEvent.payloadPreview ?? "—"}</p>
              </div>
              <div>
                <p className="text-xs font-medium text-neutral-500">Payload</p>
                <pre className="max-h-40 overflow-auto rounded bg-neutral-900 p-2 text-xs text-neutral-400">
                  {JSON.stringify(selectedEvent.payload ?? {}, null, 2)}
                </pre>
              </div>
            </div>
          )}
        </SheetContent>
      </Sheet>
    </div>
  );
}

export default function EventsPage() {
  return (
    <Suspense fallback={<PageSkeleton title subtitle tableRows={8} />}>
      <EventsContent />
    </Suspense>
  );
}
