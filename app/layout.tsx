import type { Metadata } from "next";
import "@/app/globals.css";

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
    <html lang="en" className="dark">
      <body className="min-h-screen bg-neutral-950 text-neutral-100">
        {children}
      </body>
    </html>
  );
}
