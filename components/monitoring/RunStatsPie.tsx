"use client";

import React from "react";
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from "recharts";
import type { TenantRunsResponse } from "@/lib/apiClient";

const COLORS = {
  completed: "#22c55e",
  partial: "#eab308",
  failed: "#ef4444",
  other: "#64748b",
};

type Props = {
  stats: TenantRunsResponse["stats"];
  className?: string;
};

export const RunStatsPie: React.FC<Props> = ({ stats, className }) => {
  const other = Math.max(
    0,
    stats.total - stats.completed - stats.partial - stats.failed,
  );
  const data = [
    { name: "Completed", value: stats.completed, key: "completed" as const },
    { name: "Partial", value: stats.partial, key: "partial" as const },
    { name: "Failed", value: stats.failed, key: "failed" as const },
    { name: "Other", value: other, key: "other" as const },
  ].filter((d) => d.value > 0);

  const chartData =
    data.length > 0
      ? data
      : [{ name: "No runs in page", value: 1, key: "other" as const }];

  return (
    <div className={className} style={{ width: "100%", height: 220 }}>
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie
            data={chartData}
            dataKey="value"
            nameKey="name"
            cx="50%"
            cy="50%"
            innerRadius={50}
            outerRadius={80}
            paddingAngle={2}
            label={({ name, percent }) =>
              `${name} ${(percent * 100).toFixed(0)}%`
            }
          >
            {chartData.map((entry) => (
              <Cell
                key={entry.name}
                fill={COLORS[entry.key]}
              />
            ))}
          </Pie>
          <Tooltip
            contentStyle={{
              backgroundColor: "rgba(15,23,42,0.95)",
              border: "1px solid rgba(148,163,184,0.3)",
              borderRadius: 8,
            }}
          />
          <Legend />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
};
