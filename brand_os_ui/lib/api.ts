const API_BASE = process.env.NEXT_PUBLIC_BRAND_OS_API_URL || "http://127.0.0.1:8000";

export interface RunPayload {
  tenant_id: string;
  platform: string;
  topic_hint: string;
  trace_id?: string;
  extra_context?: { signals?: unknown[]; memory_entries?: unknown[] };
}

export interface RunResult {
  trace_id: string;
  tenant_id: string;
  platform: string;
  topic_hint: string;
  content: { headline: string; body: string; hook_used: string; cta_used: string };
  visual_spec: { image_prompt: string; aspect_ratio: string; format: string; alt_text: string };
  recommendations: { suggested_timing?: string; hook_rotation?: string[]; cta_rotation?: string[]; next_topic_hints?: string[] };
  status: string;
}

export async function runBrandOs(payload: RunPayload): Promise<RunResult> {
  const res = await fetch(`${API_BASE}/brand-os/run`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function healthCheck(): Promise<{ status: string }> {
  const res = await fetch(`${API_BASE}/health`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}
