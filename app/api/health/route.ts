import { NextResponse } from "next/server";

const KIRP_API_BASE =
  typeof process !== "undefined" && process.env.NEXT_PUBLIC_API_URL
    ? process.env.NEXT_PUBLIC_API_URL.replace(/\/$/, "")
    : "http://localhost:8000";

const SERVICES = [
  { name: "kirp-api", url: `${KIRP_API_BASE}/health` },
  { name: "brand_os_api", url: "http://127.0.0.1:8002/health" },
  { name: "brand_os_monitoring", url: "http://127.0.0.1:8001/metrics" },
  { name: "qdrant", url: "http://127.0.0.1:6333/collections" },
  { name: "opa", url: "http://127.0.0.1:8181/health" },
];

async function checkUrl(url: string): Promise<boolean> {
  try {
    const ctrl = new AbortController();
    const t = setTimeout(() => ctrl.abort(), 3000);
    const res = await fetch(url, { method: "GET", signal: ctrl.signal });
    clearTimeout(t);
    return res.ok;
  } catch {
    return false;
  }
}

export async function GET() {
  const results = await Promise.all(
    SERVICES.map(async (s) => ({
      name: s.name,
      status: (await checkUrl(s.url)) ? "healthy" : "down",
      url: s.url,
    }))
  );
  return NextResponse.json({ services: results });
}
