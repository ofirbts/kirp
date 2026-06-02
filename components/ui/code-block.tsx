"use client";

import React from "react";
import { cn } from "@/lib/utils";

type CodeBlockProps = {
  code: string;
  language?: string;
  showLineNumbers?: boolean;
  className?: string;
};

export const CodeBlock: React.FC<CodeBlockProps> = ({
  code,
  language,
  showLineNumbers,
  className,
}) => {
  const lines = code.split("\n");
  return (
    <pre
      className={cn(
        "overflow-x-auto rounded border border-neutral-800 bg-neutral-950 p-3 text-xs text-neutral-300",
        className,
      )}
      data-language={language}
    >
      {showLineNumbers ? (
        <code className="flex">
          <span className="select-none pr-4 text-right text-neutral-600" aria-hidden>
            {lines.map((_, i) => (
              <span key={i} className="block">
                {i + 1}
              </span>
            ))}
          </span>
          <span className="flex-1 whitespace-pre">{code}</span>
        </code>
      ) : (
        <code className="whitespace-pre">{code}</code>
      )}
    </pre>
  );
};
