"use client";

import { useState } from "react";
import { runBrandOs, RunResult } from "@/lib/api";
import PostCard from "./PostCard";
import VisualCard from "./VisualCard";

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
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <form onSubmit={handleSubmit} className="max-w-md space-y-4">
        <div>
          <label className="block text-sm font-medium text-primary mb-1">Tenant ID</label>
          <input
            type="text"
            value={tenantId}
            onChange={(e) => setTenantId(e.target.value)}
            className="w-full border border-neutral-100 rounded px-3 py-2 text-primary"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-primary mb-1">Platform</label>
          <select
            value={platform}
            onChange={(e) => setPlatform(e.target.value)}
            className="w-full border border-neutral-100 rounded px-3 py-2 text-primary"
          >
            <option value="linkedin">LinkedIn</option>
            <option value="twitter">Twitter</option>
            <option value="whatsapp">WhatsApp</option>
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium text-primary mb-1">Topic hint</label>
          <input
            type="text"
            value={topicHint}
            onChange={(e) => setTopicHint(e.target.value)}
            placeholder="e.g. API release"
            required
            className="w-full border border-neutral-100 rounded px-3 py-2 text-primary"
          />
        </div>
        <button
          type="submit"
          disabled={loading}
          className="bg-primary text-white px-4 py-2 rounded hover:bg-primary/90 disabled:opacity-50"
        >
          {loading ? "Running…" : "Run"}
        </button>
      </form>
      {error && <p className="mt-4 text-accent">{error}</p>}
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
