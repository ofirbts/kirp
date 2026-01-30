"use client";

import React from "react";
import { Card } from "@/components/ui/card";
import type { Event } from "@/lib/types";

type EventRatePoint = {
  bucketLabel: string;
  count: number;
};

type EventRateChartProps = {
  events: Event[];
};

export const EventRateChart: React.FC<EventRateChartProps> = ({ events }) => {
  const [series, setSeries] = React.useState<EventRatePoint[]>([]);

  React.useEffect(() => {
    // Default: derive a simple 5-bucket histogram from the currently loaded events.
    if (!events || events.length === 0) {
      setSeries([]);
      return;
    }
    const buckets: Record<string, number> = {};
    for (const evt of events) {
      const key = evt.topic || "other";
      buckets[key] = (buckets[key] ?? 0) + 1;
    }
    const points: EventRatePoint[] = Object.entries(buckets)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 5)
      .map(([topic, count]) => ({ bucketLabel: topic, count }));
    setSeries(points);
  }, [events]);

  if (series.length === 0) {
    return (
      <Card className="border-neutral-800 bg-neutral-900/80 px-3 py-2 text-xs">
        <p className="mb-1 font-medium text-neutral-200">
          Event distribution
        </p>
        <p className="text-[11px] text-neutral-500">
          No recent events available to compute a distribution yet.
        </p>
      </Card>
    );
  }

  const maxCount = Math.max(...series.map((p) => p.count), 1);

  return (
    <Card className="border-neutral-800 bg-neutral-900/80 px-3 py-2 text-xs">
      <div className="mb-2 flex items-center justify-between">
        <p className="font-medium text-neutral-200">Event distribution</p>
        <span className="text-[10px] text-neutral-500">
          top {series.length} topics
        </span>
      </div>
      <div className="space-y-1">
        {series.map((p) => (
          <div key={p.bucketLabel} className="flex items-center gap-2">
            <span className="w-24 truncate text-[11px] text-neutral-400">
              {p.bucketLabel}
            </span>
            <div className="flex-1">
              <div className="h-2 w-full overflow-hidden rounded-full bg-neutral-800">
                <div
                  className="h-full rounded-full bg-cyan-500"
                  style={{ width: `${(p.count / maxCount) * 100}%` }}
                />
              </div>
            </div>
            <span className="w-8 text-right text-[10px] text-neutral-500">
              {p.count}
            </span>
          </div>
        ))}
      </div>
    </Card>
  );
};

