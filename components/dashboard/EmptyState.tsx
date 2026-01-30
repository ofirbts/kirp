"use client";

import React from "react";
import { Inbox } from "lucide-react";
import { cn } from "@/lib/utils";

type EmptyStateProps = {
  title: string;
  description?: string;
  className?: string;
};

export const EmptyState: React.FC<EmptyStateProps> = ({
  title,
  description,
  className,
}) => {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center rounded-lg border border-neutral-800 bg-neutral-900/50 px-6 py-12 text-center",
        className,
      )}
    >
      <Inbox className="mb-3 h-10 w-10 text-neutral-600" />
      <p className="text-sm font-medium text-neutral-300">{title}</p>
      {description && (
        <p className="mt-1 text-xs text-neutral-500">{description}</p>
      )}
    </div>
  );
};
