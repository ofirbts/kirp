import { NextResponse } from "next/server";

export async function GET() {
  return NextResponse.json({
    containers: [
      { name: "kirp-api", status: "running", ports: "8000" },
      { name: "kirp-worker", status: "running", ports: "" },
      { name: "kirp-dashboard", status: "running", ports: "8501" },
      { name: "kirp-postgres", status: "running", ports: "5432" },
      { name: "kirp-redis", status: "running", ports: "6379" },
      { name: "kirp-mongodb", status: "running", ports: "27017" },
      { name: "kirp-qdrant", status: "running", ports: "6333" },
      { name: "kirp-kafka", status: "running", ports: "9092" },
      { name: "kirp-zookeeper", status: "running", ports: "2181" },
      { name: "kirp-opa", status: "running", ports: "8181" },
    ],
  });
}
