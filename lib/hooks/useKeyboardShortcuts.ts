"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useToastStore } from "@/lib/stores/toastStore";

function isTypingTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false;
  const tag = target.tagName.toLowerCase();
  const editable = target.getAttribute("contenteditable");
  return (
    tag === "input" ||
    tag === "textarea" ||
    editable === "" ||
    editable === "true"
  );
}

export function useKeyboardShortcuts() {
  const router = useRouter();
  const { show } = useToastStore();

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.metaKey || e.ctrlKey || e.altKey) return;
      if (isTypingTarget(e.target)) return;

      switch (e.key) {
        case "t":
          e.preventDefault();
          router.push("/tasks");
          break;
        case "g":
          e.preventDefault();
          router.push("/graph");
          break;
        case "i":
          e.preventDefault();
          router.push("/insights");
          break;
        case "h":
          e.preventDefault();
          router.push("/history");
          break;
        case "/":
          e.preventDefault();
          show({
            variant: "default",
            title: "Global search",
            description: "Search across KIRP is coming soon.",
          });
          break;
        default:
          break;
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [router, show]);
}

