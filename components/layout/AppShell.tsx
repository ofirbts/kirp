"use client";

import React from "react";
import { SideNav } from "@/components/navigation/SideNav";
import { TopBar } from "@/components/navigation/TopBar";
import { ToastRegion } from "@/components/feedback/ToastRegion";
import { ErrorBoundary } from "@/components/layout/ErrorBoundary";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent } from "@/components/ui/sheet";
import { Menu } from "lucide-react";
import { useRouter, usePathname } from "next/navigation";
import { useAuthStore } from "@/lib/stores/authStore";
import { useTenantContextStore } from "@/lib/stores/tenantContextStore";
import { DEFAULT_TENANT_ID } from "@/lib/constants";
import { MobileNav } from "@/components/navigation/MobileNav";
import { AnimatePresence, motion } from "framer-motion";
import { useKeyboardShortcuts } from "@/lib/hooks/useKeyboardShortcuts";

export const AppShell: React.FC<React.PropsWithChildren> = ({ children }) => {
  const router = useRouter();
  const pathname = usePathname();
  const { user, loaded, loadUser } = useAuthStore();
  const [mobileNavOpen, setMobileNavOpen] = React.useState(false);

  useKeyboardShortcuts();

  // Sync tenantContextStore with auth so all API calls use correct tenant_id/user_id
  React.useEffect(() => {
    if (user) {
      useTenantContextStore.setState({
        tenantId: user.tenant_id ?? DEFAULT_TENANT_ID,
        userId: user.id ?? "",
      });
    } else {
      useTenantContextStore.setState({
        tenantId: DEFAULT_TENANT_ID,
        userId: "",
      });
    }
  }, [user]);

  // Auth guard; can be disabled in dev by env flag (SKIP_AUTH).
  React.useEffect(() => {
    loadUser();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  
  React.useEffect(() => {
    if (typeof window === "undefined") return;
    const skipAuth =
      process.env.NEXT_PUBLIC_SKIP_AUTH === "1" ||
      window.localStorage.getItem("kirp_skip_auth") === "1";
    const isAuthRoute =
      pathname === "/login" ||
      pathname === "/signup" ||
      pathname === "/reset-password";
    // Billing supports Kirp API keys from onboarding without dashboard JWT (dry-run / API customers).
    const isBillingKirpRoute = pathname === "/billing" || pathname.startsWith("/billing/");
    if (!skipAuth && loaded && !user && !isAuthRoute && !isBillingKirpRoute) {
      router.push("/login");
    }
  }, [user, loaded, pathname, router]);

  return (
    <ErrorBoundary>
      <div
        className="flex h-screen w-screen overflow-hidden bg-bg text-textMain p-4 gap-4"
        suppressHydrationWarning
      >
        {/* Desktop sidebar */}
        <aside className="hidden md:flex w-64 flex-col glass-card rounded-2xl overflow-hidden shadow-soft">
          <SideNav />
        </aside>

        {/* Main column */}
        <div className="flex min-w-0 flex-1 flex-col gap-4" suppressHydrationWarning>
          {/* Topbar as floating glass card */}
          <header className="h-16 glass-card rounded-2xl flex items-center px-4 md:px-6 justify-between">
            {/* Mobile: hamburger + compact title handled inside TopBar */}
            <div className="flex items-center gap-2 md:hidden">
              <Button
                size="sm"
                variant="ghost"
                className="h-9 w-9 rounded-full bg-surface2 text-textMain"
                onClick={() => setMobileNavOpen(true)}
              >
                <Menu className="h-4 w-4" />
              </Button>
            </div>
            <div className="flex-1">
              <TopBar />
            </div>
          </header>

          {/* Main content area with subtle page transition */}
          <main
            className="relative flex-1 overflow-y-auto glass-card rounded-2xl p-4 md:p-6"
            suppressHydrationWarning
          >
            <AnimatePresence mode="wait" initial={false}>
              <motion.div
                key={pathname}
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -6 }}
                transition={{ duration: 0.15, ease: "easeOut" }}
              >
                <div className="mx-auto max-w-7xl" suppressHydrationWarning>
                  {children}
                </div>
              </motion.div>
            </AnimatePresence>
          </main>
        </div>

        <ToastRegion />

        {/* Mobile bottom navigation */}
        <MobileNav />

        {/* Mobile sidebar drawer */}
        <Sheet open={mobileNavOpen} onOpenChange={setMobileNavOpen}>
          <SheetContent
            side="left"
            className="w-64 p-0 glass-card rounded-none border-none bg-surface1/95"
          >
            <SideNav />
          </SheetContent>
        </Sheet>
      </div>
    </ErrorBoundary>
  );
};
