"use client";

import React from "react";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { cn } from "@/lib/utils";

type PageSkeletonProps = {
  title?: boolean;
  subtitle?: boolean;
  cards?: number;
  tableRows?: number;
  className?: string;
};

export const PageSkeleton: React.FC<PageSkeletonProps> = ({
  title = true,
  subtitle = true,
  cards = 0,
  tableRows = 5,
  className,
}) => {
  return (
    <div className={cn("space-y-6", className)}>
      <div>
        {title && (
          <div className="mb-1 h-7 w-48 animate-pulse rounded bg-neutral-800" />
        )}
        {subtitle && (
          <div className="h-4 w-72 animate-pulse rounded bg-neutral-800/80" />
        )}
      </div>
      {cards > 0 && (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: cards }).map((_, i) => (
            <Card
              key={i}
              className="border-neutral-800 bg-neutral-900/70"
            >
              <CardHeader className="pb-2">
                <div className="h-4 w-24 animate-pulse rounded bg-neutral-700" />
              </CardHeader>
              <CardContent>
                <div className="h-8 w-16 animate-pulse rounded bg-neutral-700" />
              </CardContent>
            </Card>
          ))}
        </div>
      )}
      <Card className="border-neutral-800 bg-neutral-900/70">
        <CardHeader>
          <div className="h-5 w-32 animate-pulse rounded bg-neutral-700" />
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {Array.from({ length: tableRows }).map((_, i) => (
              <div
                key={i}
                className="h-10 w-full animate-pulse rounded bg-neutral-800"
              />
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
};
