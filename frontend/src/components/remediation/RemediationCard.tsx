"use client";

import { useState } from "react";
import { RemediationItem } from "@/lib/types";
import { CommandBlock } from "./CommandBlock";

interface RemediationCardProps {
  item: RemediationItem;
  onApprove?: (id: string) => void;
}

const SEVERITY_STYLES: Record<string, string> = {
  critical: "border-l-red-500 bg-red-500/5",
  warning: "border-l-amber-500 bg-amber-500/5",
  info: "border-l-blue-500 bg-blue-500/5",
  pass: "border-l-green-500 bg-green-500/5",
};

const SEVERITY_BADGE: Record<string, string> = {
  critical: "bg-red-500/20 text-red-400",
  warning: "bg-amber-500/20 text-amber-400",
  info: "bg-blue-500/20 text-blue-400",
  pass: "bg-green-500/20 text-green-400",
};

const RISK_BADGE: Record<string, string> = {
  low: "bg-green-500/10 text-green-400",
  medium: "bg-amber-500/10 text-amber-400",
  high: "bg-orange-500/10 text-orange-400",
  critical: "bg-red-500/10 text-red-400",
};

export function RemediationCard({ item, onApprove }: RemediationCardProps) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div
      className={`glass-card rounded-xl border-l-4 ${SEVERITY_STYLES[item.severity]} transition-all duration-200 hover:bg-surface-bright/40`}
    >
      {/* Header — always visible */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full text-left p-5 flex items-start gap-4"
      >
        {/* Order number */}
        <div className="flex-shrink-0 w-10 h-10 rounded-lg bg-surface-container-lowest/60 flex items-center justify-center border border-outline-variant/10">
          <span className="font-[var(--font-headline-stack)] text-lg font-bold text-primary-container">
            {item.order}
          </span>
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap mb-1">
            <h3 className="font-[var(--font-headline-stack)] font-bold text-sm uppercase tracking-tight">
              {item.title}
            </h3>
            {item.auto_resolves && (
              <span className="text-[10px] font-[var(--font-headline-stack)] uppercase tracking-widest px-2 py-0.5 rounded-full bg-surface-container-highest/60 text-on-surface/40 border border-outline-variant/10">
                Auto-resolves
              </span>
            )}
          </div>

          <div className="flex items-center gap-2 flex-wrap">
            <span className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded-full ${SEVERITY_BADGE[item.severity]}`}>
              {item.severity}
            </span>
            <span className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded-full ${RISK_BADGE[item.risk_level]}`}>
              Risk: {item.risk_level}
            </span>
            {item.estimated_downtime && (
              <span className="text-[10px] text-on-surface/40">
                Downtime: {item.estimated_downtime}
              </span>
            )}
            {item.namespace && (
              <span className="text-[10px] text-on-surface/30 font-mono">
                {item.namespace}
              </span>
            )}
          </div>
        </div>

        {/* Expand icon */}
        <span className={`material-symbols-outlined text-on-surface/30 transition-transform duration-200 ${expanded ? "rotate-180" : ""}`}>
          expand_more
        </span>
      </button>

      {/* Expanded content */}
      {expanded && (
        <div className="px-5 pb-5 pt-0 space-y-4 border-t border-outline-variant/10 mt-0">
          {/* Auto-resolve notice */}
          {item.auto_resolves && (
            <div className="flex items-center gap-2 p-3 rounded-lg bg-surface-container-highest/40 border border-outline-variant/10">
              <span className="material-symbols-outlined text-sm text-on-surface/40">info</span>
              <p className="text-xs text-on-surface/50">
                This issue may resolve automatically after upstream fixes are applied. Monitor before taking action.
              </p>
            </div>
          )}

          {/* Description */}
          {item.description && (
            <p className="text-sm text-on-surface/60 leading-relaxed">{item.description}</p>
          )}

          {/* Evidence */}
          {item.evidence_summary && (
            <div className="p-3 rounded-lg bg-surface-container-lowest/40 border border-outline-variant/10">
              <span className="font-[var(--font-headline-stack)] text-[10px] uppercase tracking-widest text-on-surface/40 block mb-1">
                Evidence
              </span>
              <p className="text-xs text-on-surface/50 font-mono">{item.evidence_summary}</p>
            </div>
          )}

          {/* Commands */}
          {item.commands.length > 0 && (
            <CommandBlock commands={item.commands} label="Commands" />
          )}

          {/* Rollback */}
          {item.rollback_commands.length > 0 && (
            <CommandBlock commands={item.rollback_commands} label="Rollback" />
          )}

          {/* Approval */}
          {item.requires_approval && onApprove && (
            <div className="flex items-center gap-3 pt-2">
              <button
                onClick={() => onApprove(item.id)}
                disabled={item.approved}
                className={`px-4 py-2 rounded-lg font-[var(--font-headline-stack)] text-xs font-bold uppercase tracking-widest transition-all ${
                  item.approved
                    ? "bg-green-500/20 text-green-400 border border-green-500/30 cursor-default"
                    : "bg-primary-container/20 text-primary-container border border-primary-container/30 hover:bg-primary-container/30 active:scale-95"
                }`}
              >
                {item.approved ? "Approved" : "Approve"}
              </button>
              {item.approved && (
                <span className="text-xs text-green-400/60">
                  <span className="material-symbols-outlined text-sm align-middle">check_circle</span> Ready for execution
                </span>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
