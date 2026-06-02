"use client";

import React from "react";

type ErrorBoundaryProps = {
  children: React.ReactNode;
};

type ErrorBoundaryState = {
  hasError: boolean;
};

/**
 * Simple error boundary to prevent a single component failure from
 * blanking the whole app. In production we could also report errors
 * to an observability backend.
 */
export class ErrorBoundary extends React.Component<
  ErrorBoundaryProps,
  ErrorBoundaryState
> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(): ErrorBoundaryState {
    return { hasError: true };
  }

  override componentDidCatch(error: unknown, errorInfo: unknown) {
    // eslint-disable-next-line no-console
    console.error("ErrorBoundary caught an error", error, errorInfo);
  }

  override render(): React.ReactNode {
    if (this.state.hasError) {
      return (
        <div className="flex h-full items-center justify-center bg-neutral-950 text-neutral-100">
          <div className="max-w-md space-y-2 rounded-md border border-red-700 bg-red-950/40 px-4 py-3 text-sm">
            <h2 className="text-base font-semibold text-red-200">
              Something went wrong
            </h2>
            <p className="text-xs text-red-100">
              The UI encountered an unexpected error. Try refreshing the page.
              If the problem persists, contact the on-call operator.
            </p>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

