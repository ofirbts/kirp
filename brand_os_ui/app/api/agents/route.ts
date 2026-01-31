import { NextResponse } from "next/server";

export async function GET() {
  const agents = [
    { id: "CONTEXT_SCANNER", name: "Context Scanner", phase: "context", role: "Scan and synthesize world context." },
    { id: "STRATEGIC_PLANNER", name: "Strategic Planner", phase: "strategy", role: "Turn context into strategy brief." },
    { id: "TECHNICAL_STORYTELLER", name: "Technical Storyteller", phase: "creation", role: "Draft first version." },
    { id: "HUMAN_EDGE", name: "Human Edge", phase: "creation", role: "Polish for clarity and platform-native feel." },
    { id: "IDENTITY_GUARDIAN", name: "Identity Guardian", phase: "quality", role: "Gatekeeper: identity and tone." },
    { id: "SKEPTICAL_CTO", name: "Skeptical CTO", phase: "quality", role: "Gatekeeper: technical accuracy." },
    { id: "VISUAL_GENERATOR", name: "Visual Generator", phase: "distribution", role: "Produce visual spec." },
    { id: "GROWTH_ANALYST", name: "Growth Analyst", phase: "distribution", role: "Recommendations." },
  ];
  return NextResponse.json(agents);
}
