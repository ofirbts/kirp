"use client";

import React from "react";
import { SideNav } from "@/components/navigation/SideNav";
import { TopBar } from "@/components/navigation/TopBar";
import { ToastRegion } from "@/components/feedback/ToastRegion";
import { ErrorBoundary } from "@/components/layout/ErrorBoundary";

/**
 * AppShell
 *
 * Top-level application chrome:
 * - Dark-mode background
 * - Persistent left navigation
 * - Top bar with section context
 */
export const AppShell: React.FC<React.PropsWithChildren> = ({ children }) => {
  return (
    <ErrorBoundary>
      <div className="flex h-screen w-screen overflow-hidden bg-neutral-950 text-neutral-100" suppressHydrationWarning>
        <SideNav />
        <div className="flex min-w-0 flex-1 flex-col" suppressHydrationWarning>
          <TopBar />
          <main className="flex-1 overflow-y-auto bg-neutral-950/90 px-3 py-3 sm:px-6 sm:py-4" suppressHydrationWarning>
            <div className="mx-auto max-w-7xl" suppressHydrationWarning>{children}</div>
          </main>
        </div>
        <ToastRegion />
      </div>
    </ErrorBoundary>
  );
};

