"use client";

import type { AnalysisStatus } from "@/lib/types";

const phaseLabels: Record<string, string> = {
  extracting: "Extracting bundle",
  parsing_complete: "Bundle parsed",
  heuristic_pass: "Running heuristic analysis",
  heuristic_complete: "Heuristic pass complete",
  ai_analysis: "AI deep analysis",
  synthesis: "Synthesizing root cause",
  complete: "Analysis complete",
  ai_skipped: "AI analysis skipped",
};

export function StreamStatus({
  status,
  findingCount,
  isComplete,
  error,
}: {
  status: AnalysisStatus | null;
  findingCount: number;
  isComplete: boolean;
  error: string | null;
}) {
  if (error) {
    return (
      <div className="flex items-center gap-3 glass-card rounded-xl px-5 py-4 border-red-500/30">
        <span className="material-symbols-outlined text-red-400">error</span>
        <div>
          <p className="text-sm font-bold font-[var(--font-headline-stack)] uppercase tracking-wider text-red-400">
            Analysis error
          </p>
          <p className="text-xs text-red-400/70">{error}</p>
        </div>
      </div>
    );
  }

  if (isComplete) {
    return (
      <div className="flex items-center gap-3 glass-card rounded-xl px-5 py-4 border-emerald-500/30">
        <span className="material-symbols-outlined text-emerald-400">check_circle</span>
        <div>
          <p className="text-sm font-bold font-[var(--font-headline-stack)] uppercase tracking-wider text-emerald-400">
            Analysis complete
          </p>
          <p className="text-xs text-emerald-400/70">
            Found {findingCount} findings
          </p>
        </div>
      </div>
    );
  }

  if (!status) {
    return (
      <div className="flex items-center gap-3 glass-card rounded-xl px-5 py-4">
        <span className="material-symbols-outlined text-on-surface/40 animate-pulse">
          progress_activity
        </span>
        <p className="text-sm text-on-surface/50">Starting analysis...</p>
      </div>
    );
  }

  const label = phaseLabels[status.phase] || status.phase;

  return (
    <div className="flex items-center gap-3 glass-card rounded-xl px-5 py-4 border-primary-container/20">
      <span className="material-symbols-outlined text-primary-container animate-pulse">
        progress_activity
      </span>
      <div className="flex-1">
        <div className="flex items-center justify-between">
          <p className="text-sm font-bold font-[var(--font-headline-stack)] uppercase tracking-wider">
            {label}
          </p>
          {status.progress && (
            <span className="text-[10px] text-on-surface/40 font-[var(--font-headline-stack)] uppercase tracking-widest">
              {status.progress}
            </span>
          )}
        </div>
        <p className="text-xs text-on-surface/50">{status.message}</p>
        {findingCount > 0 && (
          <p className="text-xs text-primary-container/70 mt-0.5">
            {findingCount} findings so far
          </p>
        )}
      </div>
    </div>
  );
}
