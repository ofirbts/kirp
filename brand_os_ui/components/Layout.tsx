"use client";

import Link from "next/link";

export default function Layout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen flex flex-col">
      <header className="bg-primary text-white px-6 py-4 flex items-center gap-6">
        <Link href="/dashboard" className="font-semibold text-lg">
          Brand OS v3
        </Link>
        <nav className="flex gap-4">
          <Link href="/dashboard" className="hover:underline">Dashboard</Link>
          <Link href="/run" className="hover:underline">Run</Link>
          <Link href="/history" className="hover:underline">History</Link>
          <Link href="/agents" className="hover:underline">Agents</Link>
          <Link href="/visuals" className="hover:underline">Visuals</Link>
        </nav>
      </header>
      <main className="flex-1 p-6">{children}</main>
    </div>
  );
}
