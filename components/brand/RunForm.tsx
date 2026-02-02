"use client";

import { useState } from "react";
import { runBrandOs, type RunResult } from "@/lib/brandOsApi";
import PostCard from "@/components/brand/PostCard";
import VisualCard from "@/components/brand/VisualCard";

export default function RunForm() {
  const [tenantId, setTenantId] = useState("default");
  const [platform, setPlatform] = useState("linkedin");
  const [topicHint, setTopicHint] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<RunResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setResult(null);
    setLoading(true);
    try {
      const data = await runBrandOs({
        tenant_id: tenantId,
        platform,
        topic_hint: topicHint,
      });
      setResult(data);
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      const isUnreachable =
        msg === "Failed to fetch" ||
        msg.includes("Connection refused") ||
        msg.includes("NetworkError") ||
        msg.includes("Load failed");
      setError(
        isUnreachable
          ? "Brand OS API is not running. Start the Brand OS service on port 8002 (or set NEXT_PUBLIC_BRAND_OS_API_URL) to use this feature."
          : msg
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <form
        onSubmit={handleSubmit}
        className="max-w-md space-y-4"
      >
        <div>
          <label className="mb-1 block text-sm font-medium text-neutral-200">
            Tenant ID
          </label>
          <input
            type="text"
            value={tenantId}
            onChange={(e) => setTenantId(e.target.value)}
            className="w-full rounded border border-neutral-700 bg-neutral-900 px-3 py-2 text-neutral-100"
          />
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium text-neutral-200">
            Platform
          </label>
          <select
            value={platform}
            onChange={(e) => setPlatform(e.target.value)}
            className="w-full rounded border border-neutral-700 bg-neutral-900 px-3 py-2 text-neutral-100"
          >
            <option value="linkedin">LinkedIn</option>
            <option value="twitter">Twitter</option>
            <option value="whatsapp">WhatsApp</option>
          </select>
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium text-neutral-200">
            Topic hint
          </label>
          <input
            type="text"
            value={topicHint}
            onChange={(e) => setTopicHint(e.target.value)}
            placeholder="e.g. API release"
            required
            className="w-full rounded border border-neutral-700 bg-neutral-900 px-3 py-2 text-neutral-100"
          />
        </div>
        <button
          type="submit"
          disabled={loading}
          className="rounded bg-cyan-600 px-4 py-2 font-medium text-white hover:bg-cyan-500 disabled:opacity-50"
        >
          {loading ? "Running…" : "Run"}
        </button>
      </form>
      {error && (
        <p className="mt-4 text-amber-400">{error}</p>
      )}
      {result && (
        <div className="mt-8 grid gap-6">
          <PostCard
            headline={result.content.headline}
            body={result.content.body}
            hook_used={result.content.hook_used}
            cta_used={result.content.cta_used}
            status={result.status}
            trace_id={result.trace_id}
          />
          <VisualCard
            image_prompt={result.visual_spec.image_prompt}
            aspect_ratio={result.visual_spec.aspect_ratio}
            format={result.visual_spec.format}
            alt_text={result.visual_spec.alt_text}
            trace_id={result.trace_id}
          />
        </div>
      )}
    </div>
  );
}
