import { NextResponse } from "next/server";

export async function GET() {
  return NextResponse.json({
    templates: [
      { id: "t1", name: "LinkedIn post", platform: "linkedin" },
      { id: "t2", name: "Twitter thread", platform: "twitter" },
    ],
  });
}
