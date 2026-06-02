"use client";

import React from "react";
import { ThinkPanel } from "@/components/dashboard/ThinkPanel";

export default function ThinkPage() {
  return (
    <div className="space-y-6" suppressHydrationWarning>
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-textMain">
          Think
        </h1>
        <p className="text-sm text-textSoft mt-1">
          Ask deeper questions over your KIRP data and get synthesized insights.
        </p>
      </div>
      <ThinkPanel />
    </div>
  );
}

