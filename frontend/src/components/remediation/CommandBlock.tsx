"use client";

import { useState } from "react";
import { RemediationCommand } from "@/lib/types";

interface CommandBlockProps {
  commands: RemediationCommand[];
  label?: string;
}

export function CommandBlock({ commands, label }: CommandBlockProps) {
  const [copied, setCopied] = useState<number | null>(null);

  const copyToClipboard = (text: string, index: number) => {
    navigator.clipboard.writeText(text);
    setCopied(index);
    setTimeout(() => setCopied(null), 2000);
  };

  if (!commands.length) return null;

  return (
    <div className="space-y-2">
      {label && (
        <span className="font-[var(--font-headline-stack)] text-[10px] uppercase tracking-widest text-on-surface/40">
          {label}
        </span>
      )}
      {commands.map((cmd, i) => (
        <div key={i} className="group">
          {cmd.description && (
            <p className="text-xs text-on-surface/50 mb-1">{cmd.description}</p>
          )}
          <div className="relative bg-surface-container-lowest/60 rounded-lg border border-outline-variant/10 p-3 font-mono text-sm text-on-surface/80 overflow-x-auto">
            <code>{cmd.command}</code>
            <button
              onClick={() => copyToClipboard(cmd.command, i)}
              className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity bg-surface-container-highest/80 px-2 py-1 rounded text-[10px] font-[var(--font-headline-stack)] uppercase tracking-widest border border-outline-variant/20 hover:border-primary-container/50"
            >
              {copied === i ? "Copied" : "Copy"}
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}
