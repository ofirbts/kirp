"use client";

import React from "react";
import { X } from "lucide-react";
import { useToastStore } from "@/lib/stores/toastStore";
import { cn } from "@/lib/utils";

export const ToastRegion: React.FC = () => {
  const { toasts, dismiss } = useToastStore();

  if (toasts.length === 0) return null;

  return (
    <div
      className="pointer-events-none fixed inset-x-0 bottom-0 z-50 flex flex-col items-center space-y-2 pb-4"
      aria-live="polite"
      aria-atomic="true"
    >
      {toasts.map((toast) => (
        <div
          key={toast.id}
          className={cn(
            "pointer-events-auto w-full max-w-sm rounded-md border px-3 py-2 text-sm shadow-lg backdrop-blur",
            "border-neutral-700 bg-neutral-900/95 text-neutral-100",
            toast.variant === "success" && "border-emerald-500/70",
            toast.variant === "error" && "border-red-500/70",
            toast.variant === "warning" && "border-amber-500/70",
          )}
        >
          <div className="flex items-start gap-2">
            <div className="flex-1">
              {toast.title && (
                <p className="text-xs font-semibold text-neutral-100">
                  {toast.title}
                </p>
              )}
              {toast.description && (
                <p className="mt-0.5 text-[11px] text-neutral-300">
                  {toast.description}
                </p>
              )}
            </div>
            <button
              type="button"
              aria-label="Dismiss notification"
              className="mt-0.5 inline-flex h-5 w-5 items-center justify-center rounded-full bg-neutral-800 text-neutral-400 hover:bg-neutral-700 hover:text-neutral-100"
              onClick={() => dismiss(toast.id)}
            >
              <X className="h-3 w-3" />
            </button>
          </div>
        </div>
      ))}
    </div>
  );
};

