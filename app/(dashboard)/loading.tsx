/**
 * Dashboard segment loading — shown while a (dashboard) child route is loading.
 * Renders inside AppShell (dashboard layout) so the shell is already visible.
 */
export default function DashboardLoading() {
  return (
    <div className="flex flex-1 items-center justify-center p-8" aria-busy="true" aria-label="Loading">
      <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
    </div>
  );
}
