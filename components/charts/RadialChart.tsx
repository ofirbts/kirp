"use client";

import React from "react";
import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from "recharts";

type RadialChartDatum = { name: string; value: number };

type RadialChartProps = {
  data: RadialChartDatum[];
  height?: number;
  className?: string;
};

const COLORS = ["#06b6d4", "#8b5cf6", "#22c55e", "#eab308", "#ef4444"];

export const RadialChart: React.FC<RadialChartProps> = ({
  data,
  height = 260,
  className,
}) => {
  return (
    <div className={className} style={{ width: "100%", height }}>
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie
            data={data}
            cx="50%"
            cy="50%"
            innerRadius={60}
            outerRadius={90}
            paddingAngle={2}
            dataKey="value"
            nameKey="name"
            label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
          >
            {data.map((_, index) => (
              <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
            ))}
          </Pie>
          <Tooltip
            contentStyle={{
              backgroundColor: "rgb(23 23 23)",
              border: "1px solid rgb(38 38 38)",
              borderRadius: "6px",
            }}
            formatter={(value: number) => [value, ""]}
          />
          <Legend />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
};
