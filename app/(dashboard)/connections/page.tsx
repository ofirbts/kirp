"use client";

import React, { useCallback, useEffect, useState, Suspense } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { PageSkeleton } from "@/components/dashboard/PageSkeleton";
import { ErrorState } from "@/components/feedback/ErrorState";
import { apiClient, type ConnectorStatus } from "@/lib/apiClient";
import { DEFAULT_TENANT_ID, DEFAULT_USER_ID } from "@/lib/constants";
import { useTenantContextStore } from "@/lib/stores/tenantContextStore";
import {
  Link2,
  Link2Off,
  RefreshCw,
  AlertCircle,
  CheckCircle2,
  Circle,
  ChevronDown,
  ChevronUp,
  Mail,
  Calendar,
  MessageSquare,
  Phone,
  FileText,
  Send,
  Webhook,
} from "lucide-react";

const INTEGRATION_ICONS: Record<string, React.ReactNode> = {
  gmail: <Mail className="h-5 w-5" />,
  calendar: <Calendar className="h-5 w-5" />,
  slack: <MessageSquare className="h-5 w-5" />,
  whatsapp: <Phone className="h-5 w-5" />,
  notion: <FileText className="h-5 w-5" />,
  email: <Send className="h-5 w-5" />,
  webhook: <Webhook className="h-5 w-5" />,
};

const OAUTH_INTEGRATIONS = ["gmail", "calendar", "slack", "notion"];
const TOKEN_INTEGRATIONS = ["whatsapp", "email", "webhook"];

function formatTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  try {
    const d = new Date(iso);
    return d.toLocaleString();
  } catch {
    return String(iso);
  }
}

function ConnectorCard({
  conn,
  tenantId,
  userId,
  onRefresh,
}: {
  conn: ConnectorStatus;
  tenantId: string;
  userId: string;
  onRefresh: () => void;
}) {
  const [syncing, setSyncing] = useState(false);
  const [disconnecting, setDisconnecting] = useState(false);
  const [showErrors, setShowErrors] = useState(false);
  const [errors, setErrors] = useState<{ at: string; message: string }[]>([]);
  const [tokenForm, setTokenForm] = useState(false);
  const [tokenValue, setTokenValue] = useState("");
  const [slackChannelId, setSlackChannelId] = useState("");
  const [connectError, setConnectError] = useState<string | null>(null);

  const handleSync = useCallback(async () => {
    setSyncing(true);
    setConnectError(null);
    try {
      await apiClient.syncConnection(conn.integration, {
        tenant_id: tenantId,
        user_id: userId,
      });
      onRefresh();
    } catch (e) {
      setConnectError(e instanceof Error ? e.message : "Sync failed");
    } finally {
      setSyncing(false);
    }
  }, [conn.integration, tenantId, userId, onRefresh]);

  const handleDisconnect = useCallback(async () => {
    if (!confirm(`Disconnect ${conn.label}?`)) return;
    setDisconnecting(true);
    setConnectError(null);
    try {
      await apiClient.disconnectIntegration(conn.integration, { tenant_id: tenantId, user_id: userId });
      onRefresh();
    } catch (e) {
      setConnectError(e instanceof Error ? e.message : "Disconnect failed");
    } finally {
      setDisconnecting(false);
    }
  }, [conn.integration, conn.label, tenantId, userId, onRefresh]);

  const handleConnectToken = useCallback(async () => {
    if (!tokenValue.trim()) return;
    setConnectError(null);
    try {
      const extra =
        conn.integration === "webhook"
          ? { webhook_url: tokenValue.trim() }
          : conn.integration === "slack" && slackChannelId.trim()
            ? { channel_id: slackChannelId.trim() }
            : undefined;
      await apiClient.connectIntegration(
        conn.integration,
        { access_token: tokenValue.trim(), extra },
        { tenant_id: tenantId, user_id: userId }
      );
      setTokenForm(false);
      setTokenValue("");
      setSlackChannelId("");
      onRefresh();
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Connect failed";
      // Parse API error body (e.g. "400: {\"detail\":\"...\"}" or "500: {\"detail\":\"...\"}")
      let display = msg;
      try {
        const match = msg.match(/^\d+\s*:\s*(\{.+\})$/s);
        if (match) {
          const obj = JSON.parse(match[1]);
          const d = obj?.detail;
          display = Array.isArray(d) ? d.map((x: { msg?: string }) => x?.msg).filter(Boolean).join("; ") || msg : (d ?? msg);
        }
      } catch {
        // keep display as msg
      }
      setConnectError(display);
    }
  }, [conn.integration, tenantId, userId, tokenValue, slackChannelId, onRefresh]);

  const loadErrors = useCallback(async () => {
    const res = await apiClient.getConnectionErrors(conn.integration, { tenant_id: tenantId, user_id: userId, limit: 10 });
    setErrors(res.errors || []);
  }, [conn.integration, tenantId, userId]);

  useEffect(() => {
    if (showErrors && errors.length === 0 && conn.error_count > 0) loadErrors();
  }, [showErrors, conn.error_count, loadErrors, errors.length]);

  const isOAuth = OAUTH_INTEGRATIONS.includes(conn.integration);
  const isTokenBased = TOKEN_INTEGRATIONS.includes(conn.integration);
  const oauthStartUrl = isOAuth ? apiClient.getConnectionsOAuthStartUrl(conn.integration as "gmail" | "calendar" | "slack" | "notion", { tenant_id: tenantId, user_id: userId }) : "";

  const statusIcon =
    conn.status === "connected" ? (
      <CheckCircle2 className="h-5 w-5 text-green-500" />
    ) : conn.status === "error" ? (
      <AlertCircle className="h-5 w-5 text-amber-500" />
    ) : (
      <Circle className="h-5 w-5 text-textSoft" />
    );

  return (
    <Card className="rounded-2xl border border-[color:var(--color-border-subtle)] bg-surface1/90 shadow-soft">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-3 text-base text-textMain">
            <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary/15 text-primary">
              {INTEGRATION_ICONS[conn.integration] ?? <Link2 className="h-5 w-5" />}
            </span>
            <span>{conn.label}</span>
            {statusIcon}
          </CardTitle>
        </div>
        <p className="text-xs text-textSoft mt-1">
          Last sync: {formatTime(conn.last_sync_at)}
          {conn.last_sync_result?.ingested != null && (
            <> · Ingested: {String(conn.last_sync_result.ingested)}</>
          )}
        </p>
      </CardHeader>
      <CardContent className="space-y-3">
        {connectError && (
          <p className="text-xs text-red-400">{connectError}</p>
        )}
        <div className="flex flex-wrap gap-2">
          {conn.connected ? (
            <>
              <Button
                size="sm"
                variant="outline"
                className="rounded-full border-[color:var(--color-border-subtle)]"
                onClick={handleDisconnect}
                disabled={disconnecting}
              >
                <Link2Off className="h-4 w-4 mr-1" />
                Disconnect
              </Button>
              {(conn.integration === "gmail" || conn.integration === "calendar" || conn.integration === "slack" || conn.integration === "notion" || conn.integration === "whatsapp") && (
                <Button
                  size="sm"
                  className="rounded-full bg-primary text-bg"
                  onClick={handleSync}
                  disabled={syncing}
                >
                  <RefreshCw className={`h-4 w-4 mr-1 ${syncing ? "animate-spin" : ""}`} />
                  Sync Now
                </Button>
              )}
            </>
          ) : (
            <>
              {isOAuth && !tokenForm && (
                <a
                  href={oauthStartUrl}
                  className="inline-flex items-center rounded-full border border-primary bg-primary/10 px-3 py-2 text-sm font-medium text-primary hover:bg-primary/20"
                >
                  <Link2 className="h-4 w-4 mr-1" />
                  Connect with OAuth
                </a>
              )}
              {(isTokenBased || isOAuth) && !tokenForm && (
                <Button
                  size="sm"
                  variant="outline"
                  className="rounded-full"
                  onClick={() => setTokenForm(true)}
                >
                  <Link2 className="h-4 w-4 mr-1" />
                  {isTokenBased ? "Connect (token / URL)" : "Or use token"}
                </Button>
              )}
            </>
          )}
        </div>
        {tokenForm && (isTokenBased || isOAuth) && (
          <div className="space-y-2 pt-2 border-t border-[color:var(--color-border-subtle)]">
            <input
              type="password"
              autoComplete="off"
              placeholder={
                conn.integration === "webhook"
                  ? "Webhook URL"
                  : conn.integration === "whatsapp"
                    ? "Twilio Auth Token (from Console → API keys)"
                    : "Token or API key"
              }
              value={tokenValue}
              onChange={(e) => setTokenValue(e.target.value)}
              className="min-w-[200px] w-full rounded-xl border border-[color:var(--color-border-subtle)] bg-surface2 px-3 py-2 text-sm text-textMain placeholder:text-textSoft"
            />
            {conn.integration === "slack" && (
              <input
                type="text"
                placeholder="Channel ID (for Sync Now, e.g. C01234)"
                value={slackChannelId}
                onChange={(e) => setSlackChannelId(e.target.value)}
                className="min-w-[200px] w-full rounded-xl border border-[color:var(--color-border-subtle)] bg-surface2 px-3 py-2 text-sm text-textMain placeholder:text-textSoft"
              />
            )}
            <div className="flex gap-2 items-center">
              <Button size="sm" className="rounded-xl" onClick={handleConnectToken} disabled={!tokenValue.trim()}>
                Save
              </Button>
              <Button size="sm" variant="ghost" onClick={() => { setTokenForm(false); setTokenValue(""); setSlackChannelId(""); setConnectError(null); }}>
                Cancel
              </Button>
              {connectError && (
                <span className="text-xs text-red-400" role="alert">
                  {connectError}
                </span>
              )}
            </div>
          </div>
        )}
        {conn.error_count > 0 && (
          <div className="pt-2 border-t border-[color:var(--color-border-subtle)]">
            <button
              type="button"
              className="flex items-center gap-1 text-xs font-medium text-textSoft hover:text-textMain"
              onClick={() => { setShowErrors(!showErrors); if (!showErrors) loadErrors(); }}
            >
              {showErrors ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
              Last {conn.error_count} error(s)
            </button>
            {showErrors && (
              <ul className="mt-2 space-y-1 max-h-32 overflow-auto text-[11px] text-textSoft">
                {(errors.length ? errors : [{ at: "", message: "Loading…" }]).map((e, i) => (
                  <li key={i}>
                    {e.at ? formatTime(e.at) : ""} — {e.message}
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function ConnectionsContent() {
  const { tenantId, userId } = useTenantContextStore();
  const [connectors, setConnectors] = useState<ConnectorStatus[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiClient.listConnections({
        tenant_id: tenantId ?? DEFAULT_TENANT_ID,
        user_id: userId ?? DEFAULT_USER_ID,
      });
      setConnectors(res.connectors ?? []);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load connections");
    } finally {
      setLoading(false);
    }
  }, [tenantId, userId]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    const params = new URLSearchParams(typeof window !== "undefined" ? window.location.search : "");
    if (params.get("gmail") === "connected" || params.get("calendar") === "connected" || params.get("slack") === "connected" || params.get("notion") === "connected") {
      load();
      if (typeof window !== "undefined") window.history.replaceState({}, "", "/connections");
    }
  }, [load]);

  if (loading && connectors.length === 0) {
    return <PageSkeleton title subtitle cards={6} />;
  }

  if (error) {
    return (
      <div className="space-y-6" suppressHydrationWarning>
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-textMain">Connections</h1>
          <p className="mt-1 text-sm text-textSoft">Manage your integrated accounts.</p>
        </div>
        <ErrorState message={error} onRetry={load} />
      </div>
    );
  }

  return (
    <div className="space-y-6" suppressHydrationWarning>
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between" suppressHydrationWarning>
        <div suppressHydrationWarning>
          <h1 className="text-2xl font-bold tracking-tight text-textMain">Connections</h1>
          <p className="mt-1 text-sm text-textSoft">
            Connect Gmail, Calendar, Slack, WhatsApp, Notion, Email, and webhooks. Sync and manage from here.
          </p>
        </div>
        <Button size="sm" variant="outline" className="rounded-full" onClick={load}>
          <RefreshCw className="h-4 w-4 mr-1" />
          Refresh
        </Button>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {connectors.map((conn) => (
          <ConnectorCard
            key={conn.integration}
            conn={conn}
            tenantId={tenantId ?? DEFAULT_TENANT_ID}
            userId={userId ?? DEFAULT_USER_ID}
            onRefresh={load}
          />
        ))}
      </div>
    </div>
  );
}

export default function ConnectionsPage() {
  return (
    <Suspense fallback={<PageSkeleton title subtitle cards={6} />}>
      <ConnectionsContent />
    </Suspense>
  );
}
