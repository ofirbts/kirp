"use client";

import React, { useCallback, useMemo, useState } from "react";
import { loadStripe } from "@stripe/stripe-js";
import { Elements, PaymentElement, useElements, useStripe } from "@stripe/react-stripe-js";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

const apiBase = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/$/, "");
const stripePk = process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY || "";

function CheckoutForm({ onDone }: { onDone: () => void }) {
  const stripe = useStripe();
  const elements = useElements();
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!stripe || !elements) return;
    setBusy(true);
    setMsg(null);
    const { error } = await stripe.confirmPayment({
      elements,
      confirmParams: {
        return_url: `${typeof window !== "undefined" ? window.location.origin : ""}/onboarding`,
      },
      redirect: "if_required",
    });
    setBusy(false);
    if (error) {
      setMsg(error.message || "Payment failed");
      return;
    }
    setMsg("Payment succeeded (or processing).");
    onDone();
  };

  return (
    <form onSubmit={submit} className="space-y-4">
      <PaymentElement />
      {msg && <p className="text-sm text-muted-foreground">{msg}</p>}
      <Button type="submit" disabled={!stripe || busy}>
        {busy ? "Processing…" : "Pay & activate"}
      </Button>
    </form>
  );
}

export default function OnboardingPage() {
  const [tenantName, setTenantName] = useState("");
  const [email, setEmail] = useState("");
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [clientSecret, setClientSecret] = useState<string | null>(null);

  const stripePromise = useMemo(() => (stripePk ? loadStripe(stripePk) : null), []);

  const doOnboard = useCallback(async () => {
    setLoading(true);
    setErr(null);
    setResult(null);
    setClientSecret(null);
    try {
      const r = await fetch(`${apiBase}/api/v1/onboarding`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ tenant_name: tenantName.trim(), email: email.trim() }),
      });
      const j = await r.json().catch(() => ({}));
      if (!r.ok) {
        setErr(typeof j.detail === "string" ? j.detail : r.statusText || "Onboarding failed");
        return;
      }
      setResult(j);
      if (stripePk && j.tenant_id) {
        const pi = await fetch(`${apiBase}/api/v1/stripe/create-payment-intent`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ tenant_id: j.tenant_id, amount_cents: 500, currency: "usd" }),
        });
        const pj = await pi.json().catch(() => ({}));
        if (!pi.ok) {
          setErr(typeof pj.detail === "string" ? pj.detail : "Could not start payment");
          return;
        }
        if (pj.clientSecret) setClientSecret(pj.clientSecret as string);
      }
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Request failed");
    } finally {
      setLoading(false);
    }
  }, [tenantName, email]);

  return (
    <div className="mx-auto max-w-lg space-y-6 p-4">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">SaaS onboarding</h1>
        <p className="text-muted-foreground text-sm mt-1">
          Create tenant (trial), receive API keys, then pay with Stripe Elements.
        </p>
      </div>

      <Card className="border-neutral-800 bg-neutral-900/70">
        <CardHeader>
          <CardTitle className="text-base">1. Tenant &amp; email</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <label htmlFor="tn" className="text-sm font-medium leading-none">
              Tenant name
            </label>
            <Input
              id="tn"
              value={tenantName}
              onChange={(e) => setTenantName(e.target.value)}
              placeholder="acme"
              className="bg-neutral-950 border-neutral-700"
            />
          </div>
          <div className="space-y-2">
            <label htmlFor="em" className="text-sm font-medium leading-none">
              Email
            </label>
            <Input
              id="em"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@acme.com"
              className="bg-neutral-950 border-neutral-700"
            />
          </div>
          <Button onClick={() => void doOnboard()} disabled={loading || !tenantName.trim() || !email.trim()}>
            {loading ? "Creating…" : "Create tenant & keys"}
          </Button>
          {err && <p className="text-sm text-red-400">{err}</p>}
        </CardContent>
      </Card>

      {result && (
        <Card className="border-neutral-800 bg-neutral-900/70">
          <CardHeader>
            <CardTitle className="text-base">2. API keys (copy once)</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm font-mono break-all">
            <div>
              <span className="text-muted-foreground">tenant_id:</span> {String(result.tenant_id)}
            </div>
            <div>
              <span className="text-muted-foreground">publishable_key:</span> {String(result.publishable_key)}
            </div>
            <div>
              <span className="text-muted-foreground">secret_key:</span> {String(result.secret_key)}
            </div>
            <p className="text-xs text-muted-foreground pt-2">
              Use header{" "}
              <code className="text-foreground">Authorization: Kirp &lt;secret_key&gt;</code> on API calls.
            </p>
          </CardContent>
        </Card>
      )}

      {clientSecret && stripePromise && (
        <Card className="border-neutral-800 bg-neutral-900/70">
          <CardHeader>
            <CardTitle className="text-base">3. Stripe Elements</CardTitle>
          </CardHeader>
          <CardContent>
            <Elements stripe={stripePromise} options={{ clientSecret }}>
              <CheckoutForm onDone={() => undefined} />
            </Elements>
          </CardContent>
        </Card>
      )}

      {!stripePk && result && (
        <p className="text-xs text-muted-foreground">
          Set <code className="text-foreground">NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY</code> and{" "}
          <code className="text-foreground">STRIPE_SECRET_KEY</code> on the API to enable card payment.
        </p>
      )}
    </div>
  );
}
