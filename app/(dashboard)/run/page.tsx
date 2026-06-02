"use client";

import RunForm from "@/components/brand/RunForm";

export default function RunPage() {
  return (
    <div className="space-y-6" suppressHydrationWarning>
      <div suppressHydrationWarning>
        <h1 className="text-2xl font-bold tracking-tight text-neutral-100">Run pipeline</h1>
        <p className="mt-1 text-sm text-muted-foreground">Trigger POST /brand-os/run with tenant, platform, and topic. Requires Brand OS API on port 8002 (or NEXT_PUBLIC_BRAND_OS_API_URL).</p>
      </div>
      <div className="mt-6">
        <RunForm />
      </div>
    </div>
  );
}
