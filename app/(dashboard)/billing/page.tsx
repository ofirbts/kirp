"use client";

import React, { Suspense, useCallback, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { PageSkeleton } from "@/components/dashboard/PageSkeleton";
import { DEFAULT_TENANT_ID } from "@/lib/constants";
import { useTenantContextStore } from "@/lib/stores/tenantContextStore";
import { AlertTriangle, CreditCard, RefreshCw } from "lucide-react";

const apiBase = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/$/, "");

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return (
    window.localStorage.getItem("access_token") ??
    window.localStorage.getItem("kirp_auth_token") ??
    window.localStorage.getItem("kirp_token") ??
    process.env.NEXT_PUBLIC_DEV_TOKEN ??
    null
  );
}

export type UsageDetailsResponse = {
  tenant_id: string;
  llm_cost_used: number;
  llm_quota_limit_usd: number | null;
  quota_enabled: boolean;
  quota_remaining_usd: number | null;
  trial_days_remaining: number | null;
  trial_ends_at: string | null;
  lifecycle: string;
  suspended: boolean;
  breakdown: { model_used: string; date: string; cost_usd: number }[];
};

function BillingContent() {
  const searchParams = useSearchParams();
  const urlTenant = searchParams.get("tenant")?.trim();
  const { tenantId: storeTenant } = useTenantContextStore();
  const tenantId = urlTenant || storeTenant || DEFAULT_TENANT_ID;

  const [data, setData] = useState<UsageDetailsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [checkoutBusy, setCheckoutBusy] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    const token = getToken();
    const headers: Record<string, string> = { "Content-Type": "application/json" };
    if (token) headers["Authorization"] = `Bearer ${token}`;
    try {
      const r = await fetch(`${apiBase}/api/v1/tenant/${encodeURIComponent(tenantId)}/usage/details`, {
        credentials: "include",
        headers,
      });
      const j = await r.json().catch(() => ({}));
      if (!r.ok) {
        setError(typeof j.detail === "string" ? j.detail : r.statusText);
        return;
      }
      setData(j as UsageDetailsResponse);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load usage");
    } finally {
      setLoading(false);
    }
  }, [tenantId]);

  useEffect(() => {
    void load();
  }, [load]);

  const chartRows = useMemo(() => {
    if (!data?.breakdown?.length) return [];
    return data.breakdown.map((b) => ({
      name: `${b.date} · ${b.model_used}`,
      cost: b.cost_usd,
    }));
  }, [data]);

  const startCheckout = async () => {
    const token = getToken();
    const headers: Record<string, string> = { "Content-Type": "application/json" };
    if (token) headers["Authorization"] = `Bearer ${token}`;
    setCheckoutBusy(true);
    setError(null);
    try {
      const r = await fetch(
        `${apiBase}/api/v1/tenant/${encodeURIComponent(tenantId)}/stripe/checkout-session`,
        { method: "POST", headers, body: JSON.stringify({}) },
      );
      const j = await r.json().catch(() => ({}));
      if (!r.ok) {
        setError(typeof j.detail === "string" ? j.detail : "Checkout failed");
        return;
      }
      if (j.url && typeof window !== "undefined") {
        window.location.href = j.url as string;
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Checkout failed");
    } finally {
      setCheckoutBusy(false);
    }
  };

  if (loading && !data) {
    return <PageSkeleton title subtitle tableRows={4} />;
  }

  return (
    <div className="space-y-6 p-4 max-w-4xl mx-auto">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Billing &amp; usage</h1>
          <p className="text-muted-foreground text-sm mt-1">
            Tenant <code className="text-foreground">{tenantId}</code> — LLM spend vs quota
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={() => void load()}>
          <RefreshCw className="h-4 w-4 mr-2" />
          Refresh
        </Button>
      </div>

      {error && (
        <Card className="border-red-900/60 bg-red-950/30">
          <CardContent className="pt-4 text-sm text-red-200">{error}</CardContent>
        </Card>
      )}

      {data?.suspended && (
        <Card className="border-amber-800 bg-amber-950/40">
          <CardHeader className="pb-2">
            <CardTitle className="text-base flex items-center gap-2 text-amber-200">
              <AlertTriangle className="h-5 w-5" />
              Account suspended
            </CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-amber-100/90">
            Billing or policy blocked this tenant. Upgrade or contact support to restore access.
          </CardContent>
        </Card>
      )}

      {data?.lifecycle === "trial" && data.trial_days_remaining !== null && !data.suspended && (
        <Card className="border-cyan-900/50 bg-cyan-950/30">
          <CardContent className="pt-4 text-sm">
            <span className="text-cyan-200 font-medium">Trial: </span>
            {data.trial_days_remaining === 0
              ? "Trial ended — upgrade to continue."
              : `${data.trial_days_remaining} day(s) remaining`}
            {data.trial_ends_at ? (
              <span className="text-muted-foreground"> (ends {data.trial_ends_at})</span>
            ) : null}
          </CardContent>
        </Card>
      )}

      <div className="grid gap-4 md:grid-cols-2">
        <Card className="border-neutral-800 bg-neutral-900/70">
          <CardHeader>
            <CardTitle className="text-base">LLM spend</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            <div>
              <span className="text-muted-foreground">Used: </span>
              <span className="font-mono">${data ? data.llm_cost_used.toFixed(4) : "—"}</span>
            </div>
            <div>
              <span className="text-muted-foreground">Quota: </span>
              <span className="font-mono">
                {data?.quota_enabled && data.llm_quota_limit_usd != null
                  ? `$${data.llm_quota_limit_usd} (${data.quota_remaining_usd?.toFixed(4) ?? "—"} left)`
                  : "Unlimited (no LLM_QUOTA_LIMIT_USD)"}
              </span>
            </div>
          </CardContent>
        </Card>

        <Card className="border-neutral-800 bg-neutral-900/70">
          <CardHeader>
            <CardTitle className="text-base">Upgrade</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <p className="text-sm text-muted-foreground">
              Open Stripe Checkout (needs <code className="text-foreground">STRIPE_PRICE_ID</code> on API).
            </p>
            <Button onClick={() => void startCheckout()} disabled={checkoutBusy || data?.suspended}>
              <CreditCard className="h-4 w-4 mr-2" />
              {checkoutBusy ? "Redirecting…" : "Upgrade with Stripe"}
            </Button>
          </CardContent>
        </Card>
      </div>

      <Card className="border-neutral-800 bg-neutral-900/70">
        <CardHeader>
          <CardTitle className="text-base">Cost by model &amp; day (recent runs)</CardTitle>
        </CardHeader>
        <CardContent className="h-72">
          {chartRows.length === 0 ? (
            <p className="text-sm text-muted-foreground">No run cost data yet.</p>
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartRows} margin={{ top: 8, right: 8, left: 0, bottom: 40 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#333" />
                <XAxis dataKey="name" tick={{ fontSize: 10 }} angle={-35} textAnchor="end" height={70} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip
                  contentStyle={{ background: "#171717", border: "1px solid #333" }}
                  formatter={(v: number) => [`$${v.toFixed(6)}`, "cost"]}
                />
                <Bar dataKey="cost" fill="#22c55e" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

export default function BillingPage() {
  return (
    <Suspense fallback={<PageSkeleton title subtitle tableRows={4} />}>
      <BillingContent />
    </Suspense>
  );
}
