"use client";

import React from "react";
import type { TenantRunRow } from "@/lib/apiClient";
import { cn } from "@/lib/utils";

type Props = {
  runs: TenantRunRow[];
  onSelectRun: (runId: string) => void;
  selectedRunId: string | null;
};

function stateBadge(state: string) {
  const s = state.toLowerCase();
  const cls =
    s === "completed"
      ? "bg-green-500/15 text-green-400 border-green-500/40"
      : s === "failed"
        ? "bg-red-500/15 text-red-400 border-red-500/40"
        : s === "partial"
          ? "bg-amber-500/15 text-amber-300 border-amber-500/40"
          : "bg-slate-500/15 text-slate-300 border-slate-500/40";
  return (
    <span
      className={cn(
        "inline-flex rounded-md border px-2 py-0.5 text-[11px] font-medium capitalize",
        cls,
      )}
    >
      {state}
    </span>
  );
}

export const RunsTable: React.FC<Props> = ({
  runs,
  onSelectRun,
  selectedRunId,
}) => {
  if (runs.length === 0) {
    return (
      <p className="text-sm text-textSoft py-8 text-center">
        No runs returned for this tenant (or API unreachable).
      </p>
    );
  }

  return (
    <div className="overflow-x-auto rounded-xl border border-[color:var(--color-border-subtle)]">
      <table className="w-full text-left text-sm">
        <thead className="bg-surface2/80 text-[11px] uppercase tracking-wide text-textSoft">
          <tr>
            <th className="px-3 py-2 font-medium">run_id</th>
            <th className="px-3 py-2 font-medium">state</th>
            <th className="px-3 py-2 font-medium">workflow</th>
            <th className="px-3 py-2 font-medium">model_used</th>
            <th className="px-3 py-2 font-medium">steps</th>
            <th className="px-3 py-2 font-medium">started_at</th>
          </tr>
        </thead>
        <tbody>
          {runs.map((r) => (
            <tr
              key={r.run_id}
              role="button"
              tabIndex={0}
              onClick={() => onSelectRun(r.run_id)}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault();
                  onSelectRun(r.run_id);
                }
              }}
              className={cn(
                "cursor-pointer border-t border-[color:var(--color-border-subtle)] transition-colors hover:bg-primary/5",
                selectedRunId === r.run_id && "bg-primary/10",
              )}
            >
              <td className="px-3 py-2 font-mono text-xs text-textMain">
                {r.run_id}
              </td>
              <td className="px-3 py-2">{stateBadge(r.state)}</td>
              <td className="px-3 py-2 text-textSoft">{r.workflow_type}</td>
              <td className="px-3 py-2 font-mono text-xs text-textMain">
                {r.model ?? "—"}
              </td>
              <td className="px-3 py-2 tabular-nums text-textMain">
                {r.steps_count}
              </td>
              <td className="px-3 py-2 text-xs text-textSoft">
                {r.started_at?.slice(0, 19) ?? "—"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};
