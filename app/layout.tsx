import type { Metadata } from "next";
import "@/app/globals.css";
import { WrongPortBanner } from "@/components/WrongPortBanner";
import { ThemeProvider } from "@/components/layout/ThemeProvider";
import LLMUsageToolbar from "@/components/LLMUsageToolbar";

export const metadata: Metadata = {
  title: "KIRP Intelligence OS",
  description: "Controlled Intelligence Layer · Event-Sourced · Multi-Tenant",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="min-h-screen bg-bg text-textMain" suppressHydrationWarning>
        <ThemeProvider>
          <WrongPortBanner />
          <LLMUsageToolbar />
          {children}
        </ThemeProvider>
      </body>
    </html>
  );
}
