"use client";

import { Loader2, CheckCircle, AlertCircle } from "lucide-react";
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
      <div className="flex items-center gap-3 bg-red-500/10 border border-red-500/30 rounded-lg px-4 py-3">
        <AlertCircle className="h-5 w-5 text-red-400 shrink-0" />
        <div>
          <p className="text-sm font-medium text-red-400">Analysis error</p>
          <p className="text-xs text-red-400/70">{error}</p>
        </div>
      </div>
    );
  }

  if (isComplete) {
    return (
      <div className="flex items-center gap-3 bg-emerald-500/10 border border-emerald-500/30 rounded-lg px-4 py-3">
        <CheckCircle className="h-5 w-5 text-emerald-400 shrink-0" />
        <div>
          <p className="text-sm font-medium text-emerald-400">
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
      <div className="flex items-center gap-3 bg-muted/50 rounded-lg px-4 py-3">
        <Loader2 className="h-5 w-5 text-muted-foreground animate-spin shrink-0" />
        <p className="text-sm text-muted-foreground">Starting analysis...</p>
      </div>
    );
  }

  const label = phaseLabels[status.phase] || status.phase;

  return (
    <div className="flex items-center gap-3 bg-primary/5 border border-primary/20 rounded-lg px-4 py-3">
      <Loader2 className="h-5 w-5 text-primary animate-spin shrink-0" />
      <div className="flex-1">
        <div className="flex items-center justify-between">
          <p className="text-sm font-medium">{label}</p>
          {status.progress && (
            <span className="text-xs text-muted-foreground">
              {status.progress}
            </span>
          )}
        </div>
        <p className="text-xs text-muted-foreground">{status.message}</p>
        {findingCount > 0 && (
          <p className="text-xs text-muted-foreground mt-0.5">
            {findingCount} findings so far
          </p>
        )}
      </div>
    </div>
  );
}
