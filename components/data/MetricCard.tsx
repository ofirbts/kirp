"use client";

import React from "react";
import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";

type MetricCardProps = {
  title: string;
  value: string | number | React.ReactNode;
  description?: string;
  accent?: "normal" | "attention";
  className?: string;
};

export const MetricCard: React.FC<MetricCardProps> = ({
  title,
  value,
  description,
  accent = "normal",
  className,
}) => {
  return (
    <Card
      className={cn(
        "flex flex-col justify-between gap-2 border-neutral-800 bg-neutral-900/70 px-4 py-3 text-sm shadow-sm",
        accent === "attention" && "border-cyan-500/60 shadow-cyan-500/20",
        className,
      )}
    >
      <div className="flex items-center justify-between gap-2">
        <span className="text-xs font-medium uppercase tracking-wide text-neutral-400">
          {title}
        </span>
      </div>
      <div className="mt-1 text-2xl font-semibold tracking-tight text-neutral-50">
        {typeof value === "string" || typeof value === "number" ? (
          <span>{value}</span>
        ) : (
          value
        )}
      </div>
      {description && (
        <div className="mt-1 text-xs text-neutral-500">{description}</div>
      )}
    </Card>
  );
};

