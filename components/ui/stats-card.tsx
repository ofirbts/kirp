"use client";

import React from "react";
import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import type { LucideIcon } from "lucide-react";

type StatsCardProps = {
  title: string;
  value: string | number;
  icon?: LucideIcon;
  description?: string;
  className?: string;
};

export const StatsCard: React.FC<StatsCardProps> = ({
  title,
  value,
  icon: Icon,
  description,
  className,
}) => {
  return (
    <Card
      className={cn(
        "border-neutral-800 bg-neutral-900/70 px-4 py-3 text-sm shadow-sm",
        className,
      )}
    >
      <div className="flex items-center justify-between gap-2">
        <span className="text-xs font-medium uppercase tracking-wide text-neutral-400">
          {title}
        </span>
        {Icon && <Icon className="h-4 w-4 text-neutral-500" />}
      </div>
      <div className="mt-1 text-2xl font-semibold tracking-tight text-neutral-50">
        {value}
      </div>
      {description && (
        <div className="mt-1 text-xs text-neutral-500">{description}</div>
      )}
    </Card>
  );
};
