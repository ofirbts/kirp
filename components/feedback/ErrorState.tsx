"use client";

import React from "react";
import { Button } from "@/components/ui/button";
import { AlertTriangle } from "lucide-react";
import { cn } from "@/lib/utils";

type ErrorStateProps = {
  message: string;
  onRetry?: () => void;
  className?: string;
};

/**
 * Inline error state component for feature panels.
 * Shows a short message and an optional "Retry" action.
 */
export const ErrorState: React.FC<ErrorStateProps> = ({
  message,
  onRetry,
  className,
}) => {
  return (
    <div
      className={cn(
        "flex items-center justify-between gap-3 rounded-md border border-red-700 bg-red-950/40 px-3 py-2 text-xs text-red-200",
        className,
      )}
      role="status"
      aria-live="polite"
    >
      <div className="flex items-center gap-2">
        <AlertTriangle className="h-4 w-4 flex-shrink-0 text-red-300" />
        <span className="break-words">{message}</span>
      </div>
      {onRetry && (
        <Button
          size="sm"
          variant="outline"
          className="h-7 border-red-500/70 bg-red-950/40 text-[11px] text-red-100 hover:bg-red-900/60 hover:text-red-50"
          onClick={onRetry}
        >
          Retry
        </Button>
      )}
    </div>
  );
};

