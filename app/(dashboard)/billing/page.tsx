"use client";

import React, { Suspense, useCallback, useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
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
import { Input } from "@/components/ui/input";
import { PageSkeleton } from "@/components/dashboard/PageSkeleton";
import { DEFAULT_TENANT_ID } from "@/lib/constants";
import { useTenantContextStore } from "@/lib/stores/tenantContextStore";
import { AlertTriangle, CreditCard, KeyRound, RefreshCw, UserPlus } from "lucide-react";

const apiBase = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/$/, "");

/** Session-only: Kirp secret from onboarding (`kirp_sk_...`). */
const SS_KIRP_SECRET = "kirp_billing_secret";
const SS_KIRP_TENANT = "kirp_billing_tenant_id";

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

function getKirpSecret(): string | null {
  if (typeof window === "undefined") return null;
  const fromSession = window.sessionStorage.getItem(SS_KIRP_SECRET)?.trim();
  if (fromSession) return fromSession;
  return window.localStorage.getItem(SS_KIRP_SECRET)?.trim() || null;
}

/** Prefer Kirp (API key) when set; otherwise Bearer from dashboard login. */
function billingAuthHeaders(): Record<string, string> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  const kirp = getKirpSecret();
  if (kirp) {
    headers.Authorization = `Kirp ${kirp}`;
    return headers;
  }
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  return headers;
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
  const router = useRouter();
  const searchParams = useSearchParams();
  const urlTenant = searchParams.get("tenant")?.trim();
  const { tenantId: storeTenant } = useTenantContextStore();

  const [sessionTenantId, setSessionTenantId] = useState<string | null>(null);
  const [hydrated, setHydrated] = useState(false);

  const [dryName, setDryName] = useState("acme-dryrun");
  const [dryEmail, setDryEmail] = useState("dryrun@test.com");
  const [dryBusy, setDryBusy] = useState(false);
  const [dryMsg, setDryMsg] = useState<string | null>(null);

  const [pasteTenant, setPasteTenant] = useState("");
  const [pasteSecret, setPasteSecret] = useState("");
  const [persistKirp, setPersistKirp] = useState(false);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const t = sessionStorage.getItem(SS_KIRP_TENANT)?.trim();
    if (t) setSessionTenantId(t);
    setHydrated(true);
  }, []);

  const tenantId = urlTenant || sessionTenantId || storeTenant || DEFAULT_TENANT_ID;

  const [data, setData] = useState<UsageDetailsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [checkoutBusy, setCheckoutBusy] = useState(false);

  const loadUsageFor = useCallback(async (tid: string) => {
    setLoading(true);
    setError(null);
    const headers = billingAuthHeaders();
    if (!headers.Authorization) {
      setError("Sign in to the dashboard, or connect a Kirp API key below (from onboarding).");
      setLoading(false);
      setData(null);
      return;
    }
    try {
      const r = await fetch(`${apiBase}/api/v1/tenant/${encodeURIComponent(tid)}/usage/details`, {
        credentials: "include",
        headers,
      });
      const j = await r.json().catch(() => ({}));
      if (!r.ok) {
        setError(typeof j.detail === "string" ? j.detail : r.statusText);
        setData(null);
        return;
      }
      setData(j as UsageDetailsResponse);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load usage");
      setData(null);
    } finally {
      setLoading(false);
    }
  }, []);

  const load = useCallback(async () => {
    await loadUsageFor(tenantId);
  }, [tenantId, loadUsageFor]);

  useEffect(() => {
    if (!hydrated) return;
    void load();
  }, [hydrated, load]);

  const chartRows = useMemo(() => {
    if (!data?.breakdown?.length) return [];
    return data.breakdown.map((b) => ({
      name: `${b.date} · ${b.model_used}`,
      cost: b.cost_usd,
    }));
  }, [data]);

  const startCheckout = async () => {
    const headers = billingAuthHeaders();
    if (!headers.Authorization) {
      setError("Add a Kirp API key or sign in to start checkout.");
      return;
    }
    setCheckoutBusy(true);
    setError(null);
    const origin = typeof window !== "undefined" ? window.location.origin : "";
    const body =
      origin !== ""
        ? {
            success_url: `${origin}/billing?tenant=${encodeURIComponent(tenantId)}&checkout=success`,
            cancel_url: `${origin}/billing?tenant=${encodeURIComponent(tenantId)}&checkout=cancel`,
          }
        : {};
    try {
      const r = await fetch(
        `${apiBase}/api/v1/tenant/${encodeURIComponent(tenantId)}/stripe/checkout-session`,
        { method: "POST", headers, body: JSON.stringify(body) },
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

  function storeKirpCredentials(tid: string, secret: string) {
    if (typeof window === "undefined") return;
    const storage = persistKirp ? window.localStorage : window.sessionStorage;
    const other = persistKirp ? window.sessionStorage : window.localStorage;
    other.removeItem(SS_KIRP_SECRET);
    other.removeItem(SS_KIRP_TENANT);
    storage.setItem(SS_KIRP_SECRET, secret.trim());
    storage.setItem(SS_KIRP_TENANT, tid.trim());
    setSessionTenantId(tid.trim());
    router.replace(`/billing?tenant=${encodeURIComponent(tid.trim())}`);
  }

  async function runDryRunSignup() {
    setDryBusy(true);
    setDryMsg(null);
    setError(null);
    const unique = `${dryName}-${Date.now()}`;
    try {
      const r = await fetch(`${apiBase}/api/v1/onboarding`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ tenant_name: unique, email: dryEmail.trim() }),
      });
      const j = (await r.json().catch(() => ({}))) as Record<string, unknown>;
      if (!r.ok) {
        setDryMsg(typeof j.detail === "string" ? j.detail : `Onboarding failed (${r.status})`);
        return;
      }
      const tid = typeof j.tenant_id === "string" ? j.tenant_id : "";
      const sk = typeof j.secret_key === "string" ? j.secret_key : "";
      if (!tid || !sk) {
        setDryMsg("Onboarding response missing tenant_id or secret_key.");
        return;
      }
      storeKirpCredentials(tid, sk);
      setDryMsg("Tenant created — loading usage…");
      await loadUsageFor(tid);
      setDryMsg(null);
    } catch (e) {
      setDryMsg(e instanceof Error ? e.message : "Onboarding request failed");
    } finally {
      setDryBusy(false);
    }
  }

  function applyPastedKeys() {
    setDryMsg(null);
    const tid = pasteTenant.trim();
    const sk = pasteSecret.trim();
    if (!tid || !sk) {
      setDryMsg("Enter both tenant UUID and kirp_sk secret.");
      return;
    }
    storeKirpCredentials(tid, sk);
    void loadUsageFor(tid);
  }

  function clearKirpConnection() {
    if (typeof window !== "undefined") {
      sessionStorage.removeItem(SS_KIRP_SECRET);
      sessionStorage.removeItem(SS_KIRP_TENANT);
      localStorage.removeItem(SS_KIRP_SECRET);
      localStorage.removeItem(SS_KIRP_TENANT);
    }
    setSessionTenantId(null);
    setPasteTenant("");
    setPasteSecret("");
    setDryMsg(null);
    router.replace("/billing");
    void loadUsageFor(DEFAULT_TENANT_ID);
  }

  if (!hydrated || (loading && !data && !error)) {
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
        <Button variant="outline" size="sm" onClick={() => void load()} disabled={loading}>
          <RefreshCw className="h-4 w-4 mr-2" />
          Refresh
        </Button>
      </div>

      <Card className="border-violet-900/50 bg-violet-950/20">
        <CardHeader className="pb-2">
          <CardTitle className="text-base flex items-center gap-2 text-violet-200">
            <KeyRound className="h-5 w-5 shrink-0" />
            Kirp API key (onboarding) — dry-run signup
          </CardTitle>
          <p className="text-xs text-muted-foreground font-normal mt-1">
            Uses <code className="text-foreground">Authorization: Kirp kirp_sk_…</code> like the API. Keys stay in{" "}
            {persistKirp ? "localStorage" : "sessionStorage"} for this browser (clear below when done).
          </p>
        </CardHeader>
        <CardContent className="space-y-4 text-sm">
          <label className="flex items-center gap-2 cursor-pointer text-muted-foreground">
            <input
              type="checkbox"
              checked={persistKirp}
              onChange={(e) => setPersistKirp(e.target.checked)}
              className="rounded border-neutral-600"
            />
            Remember key across tabs / restarts (localStorage)
          </label>

          <div className="grid gap-3 md:grid-cols-2">
            <div className="space-y-2 rounded-lg border border-neutral-800 bg-neutral-950/50 p-3">
              <div className="flex items-center gap-2 text-foreground font-medium">
                <UserPlus className="h-4 w-4" />
                One-click dry-run customer
              </div>
              <div className="space-y-1">
                <label className="text-xs text-muted-foreground">Tenant name prefix</label>
                <Input value={dryName} onChange={(e) => setDryName(e.target.value)} placeholder="acme-dryrun" />
              </div>
              <div className="space-y-1">
                <label className="text-xs text-muted-foreground">Email</label>
                <Input
                  type="email"
                  value={dryEmail}
                  onChange={(e) => setDryEmail(e.target.value)}
                  placeholder="you@company.com"
                />
              </div>
              <Button type="button" size="sm" onClick={() => void runDryRunSignup()} disabled={dryBusy}>
                {dryBusy ? "Creating…" : "Create tenant & load billing"}
              </Button>
            </div>

            <div className="space-y-2 rounded-lg border border-neutral-800 bg-neutral-950/50 p-3">
              <div className="text-foreground font-medium">Already have onboarding response?</div>
              <div className="space-y-1">
                <label className="text-xs text-muted-foreground">Tenant ID (UUID)</label>
                <Input
                  value={pasteTenant}
                  onChange={(e) => setPasteTenant(e.target.value)}
                  placeholder="00000000-0000-0000-0000-000000000000"
                  className="font-mono text-xs"
                />
              </div>
              <div className="space-y-1">
                <label className="text-xs text-muted-foreground">Secret key (kirp_sk_…)</label>
                <Input
                  type="password"
                  value={pasteSecret}
                  onChange={(e) => setPasteSecret(e.target.value)}
                  placeholder="kirp_sk_…"
                  className="font-mono text-xs"
                  autoComplete="off"
                />
              </div>
              <Button type="button" size="sm" variant="secondary" onClick={() => applyPastedKeys()}>
                Apply keys &amp; load
              </Button>
            </div>
          </div>

          {dryMsg && <p className="text-amber-200 text-xs">{dryMsg}</p>}

          <div className="flex flex-wrap gap-2 pt-1">
            <Button type="button" variant="ghost" size="sm" className="text-muted-foreground" onClick={clearKirpConnection}>
              Clear stored Kirp key
            </Button>
          </div>
        </CardContent>
      </Card>

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
