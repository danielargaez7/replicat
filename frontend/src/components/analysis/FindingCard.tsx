"use client";

import { useState } from "react";
import { SeverityBadge } from "./SeverityBadge";
import type { Finding } from "@/lib/types";

export function FindingCard({ finding }: { finding: Finding }) {
  const [isOpen, setIsOpen] = useState(false);
  const hasDetails =
    (finding.evidence && finding.evidence.length > 0) || finding.remediation;

  return (
    <div className="glass-card rounded-xl overflow-hidden hover:border-md3-primary/20 transition-all">
      <button
        className="w-full text-left cursor-pointer"
        onClick={() => hasDetails && setIsOpen(!isOpen)}
      >
        <div className="py-4 px-5">
          <div className="flex items-start gap-3">
            {hasDetails && (
              <div className="mt-0.5 text-on-surface/30">
                <span className="material-symbols-outlined text-base">
                  {isOpen ? "expand_more" : "chevron_right"}
                </span>
              </div>
            )}
            <div className="flex-1 space-y-2">
              <div className="flex items-center gap-2 flex-wrap">
                <SeverityBadge severity={finding.severity} />
                <span className="font-[var(--font-headline-stack)] font-bold text-sm uppercase tracking-tight">
                  {finding.title}
                </span>
                <span className="inline-flex items-center px-2 py-0.5 rounded-md border border-outline-variant/20 bg-surface-container-highest/50 text-[10px] font-bold uppercase tracking-wider font-[var(--font-headline-stack)] text-on-surface/40">
                  {finding.source === "heuristic" ? "Heuristic" : "AI"}
                </span>
                {finding.confidence !== "high" && (
                  <span className="inline-flex items-center px-2 py-0.5 rounded-md border border-outline-variant/20 bg-surface-container-highest/50 text-[10px] font-bold uppercase tracking-wider font-[var(--font-headline-stack)] text-on-surface/40">
                    {finding.confidence} confidence
                  </span>
                )}
              </div>
              <p className="text-sm text-on-surface/50 leading-relaxed">
                {finding.description}
              </p>
              {finding.namespace && (
                <div className="flex gap-2 text-xs">
                  <span className="bg-surface-container-highest/60 text-on-surface/40 px-2 py-0.5 rounded-md font-mono text-[10px]">
                    {finding.namespace}
                  </span>
                  {finding.resource_kind && finding.resource_name && (
                    <span className="bg-surface-container-highest/60 text-on-surface/40 px-2 py-0.5 rounded-md font-mono text-[10px]">
                      {finding.resource_kind}/{finding.resource_name}
                    </span>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      </button>

      {hasDetails && isOpen && (
        <div className="pb-4 px-5 space-y-4 border-t border-outline-variant/10 pt-4">
          {finding.evidence.length > 0 && (
            <div className="space-y-2">
              <div className="flex items-center gap-2 font-[var(--font-headline-stack)] text-[10px] font-bold text-on-surface/40 uppercase tracking-[0.2em]">
                <span className="material-symbols-outlined text-xs">terminal</span>
                Evidence
              </div>
              {finding.evidence.map((ev, i) => (
                <div
                  key={i}
                  className="bg-surface-container-lowest/60 rounded-lg p-3 font-mono text-xs leading-relaxed whitespace-pre-wrap overflow-x-auto border border-outline-variant/10"
                >
                  {ev.source_file && (
                    <div className="text-on-surface/30 mb-1">
                      {ev.source_file}
                      {ev.line_number && `:${ev.line_number}`}
                    </div>
                  )}
                  <span className="text-on-surface/70">{ev.content}</span>
                </div>
              ))}
            </div>
          )}

          {finding.remediation && (
            <div className="space-y-2">
              <div className="flex items-center gap-2 font-[var(--font-headline-stack)] text-[10px] font-bold text-on-surface/40 uppercase tracking-[0.2em]">
                <span className="material-symbols-outlined text-xs">build</span>
                Remediation
              </div>
              <div className="bg-emerald-500/5 border border-emerald-500/20 rounded-lg p-3 text-sm text-emerald-300 leading-relaxed">
                {finding.remediation}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
