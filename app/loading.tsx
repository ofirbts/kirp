/**
 * Root loading UI — shown while the root segment is loading.
 * Wraps the entire app; keep minimal so static assets and shell load first.
 */
export default function RootLoading() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-bg text-textMain" aria-busy="true" aria-label="Loading">
      <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
    </div>
  );
}
