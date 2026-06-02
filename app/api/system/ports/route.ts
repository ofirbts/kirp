import { NextResponse } from "next/server";

export async function GET() {
  return NextResponse.json({
    ports: [
      { port: 8000, pid: "", command: "kirp-api or uvicorn" },
      { port: 8001, pid: "", command: "brand_os_monitoring" },
      { port: 8002, pid: "", command: "brand_os_api" },
      { port: 3100, pid: "", command: "next" },
      { port: 8501, pid: "", command: "streamlit" },
      { port: 6333, pid: "", command: "qdrant" },
      { port: 6379, pid: "", command: "redis" },
      { port: 5432, pid: "", command: "postgres" },
      { port: 8081, pid: "", command: "mongo-express" },
      { port: 9090, pid: "", command: "prometheus" },
      { port: 8181, pid: "", command: "opa" },
    ],
  });
}
