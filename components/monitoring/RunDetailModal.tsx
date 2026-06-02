"use client";

import React, { useEffect, useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { getRunStatusV1, type RunStatusResponse } from "@/lib/apiClient";
import { cn } from "@/lib/utils";

type Props = {
  runId: string | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
};

export const RunDetailModal: React.FC<Props> = ({
  runId,
  open,
  onOpenChange,
}) => {
  const [data, setData] = useState<RunStatusResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open || !runId) {
      setData(null);
      setError(null);
      return;
    }
    let cancelled = false;
    setLoading(true);
    setError(null);
    getRunStatusV1(runId)
      .then((d) => {
        if (!cancelled) setData(d);
      })
      .catch((e) => {
        if (!cancelled)
          setError(e instanceof Error ? e.message : "Failed to load run status");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [open, runId]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[85vh] max-w-3xl overflow-y-auto rounded-2xl border-[color:var(--color-border-subtle)] bg-surface1">
        <DialogHeader>
          <DialogTitle className="text-textMain">
            Run timeline
            {runId && (
              <span className="ml-2 font-mono text-sm font-normal text-textSoft">
                {runId}
              </span>
            )}
          </DialogTitle>
        </DialogHeader>
        {loading && (
          <p className="text-sm text-textSoft">Loading status…</p>
        )}
        {error && (
          <p className="text-sm text-red-400">{error}</p>
        )}
        {data && !loading && (
          <div className="space-y-4 text-sm">
            <div className="flex flex-wrap gap-3 text-textMain">
              <span>
                <span className="text-textSoft">state </span>
                <strong className="capitalize">{data.state}</strong>
              </span>
              <span>
                <span className="text-textSoft">complete </span>
                <strong>{data.is_complete ? "yes" : "no"}</strong>
              </span>
              {data.model != null && data.model !== "" && (
                <span>
                  <span className="text-textSoft">model_used </span>
                  <strong className="font-mono text-xs">{data.model}</strong>
                </span>
              )}
            </div>
            <ol className="space-y-2 border-t border-[color:var(--color-border-subtle)] pt-3">
              {data.timeline.map((step, i) => (
                <li
                  key={`${step.step}-${step.ts}-${i}`}
                  className="flex flex-wrap items-baseline gap-2 rounded-lg border border-[color:var(--color-border-subtle)] bg-surface2/50 px-3 py-2"
                >
                  <span className="font-medium text-primary">{step.step}</span>
                  <span
                    className={cn(
                      "text-xs uppercase",
                      step.status === "failed" || step.status === "error"
                        ? "text-red-400"
                        : step.status === "completed" ||
                            step.status === "success"
                          ? "text-green-400"
                          : "text-textSoft",
                    )}
                  >
                    {step.status}
                  </span>
                  <span className="text-[11px] text-textSoft">{step.ts}</span>
                  {step.error && (
                    <span className="w-full text-xs text-red-300">
                      {step.error}
                    </span>
                  )}
                </li>
              ))}
            </ol>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
};
