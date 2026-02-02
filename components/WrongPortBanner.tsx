"use client";

import React, { useEffect, useState } from "react";

const UI_PORT = typeof process !== "undefined" ? (process.env.NEXT_PUBLIC_UI_PORT || "3100") : "3100";
const CORRECT_ORIGIN = `http://localhost:${UI_PORT}`;

export function WrongPortBanner() {
  const [show, setShow] = useState(false);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const port = window.location.port;
    setShow(port !== UI_PORT);
  }, []);

  if (!show) return null;

  return (
    <div
      role="alert"
      className="fixed top-0 left-0 right-0 z-[9999] bg-amber-600 text-amber-950 px-4 py-2 text-center text-sm font-medium shadow-lg"
    >
      UI is running on the wrong port. Please open{" "}
      <a
        href={CORRECT_ORIGIN}
        className="underline font-semibold hover:no-underline"
      >
        {CORRECT_ORIGIN}
      </a>
    </div>
  );
}
