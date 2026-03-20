"use client";

import { useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { ScrollArea } from "@/components/ui/scroll-area";
import { useAnalysisStream } from "@/lib/hooks/useAnalysisStream";
import { HealthScore } from "@/components/analysis/HealthScore";
import { FindingCard } from "@/components/analysis/FindingCard";
import { StreamStatus } from "@/components/analysis/StreamStatus";
import { TimelineView } from "@/components/analysis/TimelineView";
import { ChatPanel } from "@/components/analysis/ChatPanel";
import type { Severity } from "@/lib/types";

type View = "overview" | "findings" | "timeline" | "chat";

const sidebarNav = [
  { id: "overview" as View, icon: "dashboard", label: "Dashboard", fill: true },
  { id: "findings" as View, icon: "analytics", label: "Analysis" },
  { id: "timeline" as View, icon: "terminal", label: "Log Explorer" },
  { id: "chat" as View, icon: "monitor_heart", label: "AI Chat" },
];

const topTabs = [
  { id: "overview" as View, label: "Overview" },
  { id: "findings" as View, label: "Findings" },
  { id: "timeline" as View, label: "Timeline" },
  { id: "chat" as View, label: "Chat" },
];

export default function AnalysisPage() {
  const params = useParams();
  const analysisId = params.id as string;
  const { status, findings, result, error, isStreaming, isComplete, startStream } =
    useAnalysisStream(analysisId);
  const [activeView, setActiveView] = useState<View>("overview");
  const [severityFilter, setSeverityFilter] = useState<Severity | "all">("all");

  useEffect(() => {
    startStream();
  }, [startStream]);

  const filteredFindings = useMemo(() => {
    if (severityFilter === "all") return findings;
    return findings.filter((f) => f.severity === severityFilter);
  }, [findings, severityFilter]);

  const severityCounts = useMemo(() => {
    const counts = { critical: 0, warning: 0, info: 0, pass: 0 };
    findings.forEach((f) => {
      if (f.severity in counts) counts[f.severity as keyof typeof counts]++;
    });
    return counts;
  }, [findings]);

  const healthScore = result?.health_score ?? (isComplete ? 100 : -1);
  const totalFindings = severityCounts.critical + severityCounts.warning + severityCounts.info + severityCounts.pass;

  const healthLabel = healthScore >= 90
    ? "HEALTHY"
    : healthScore >= 70
      ? "DEGRADED"
      : healthScore >= 40
        ? "UNHEALTHY"
        : healthScore >= 0
          ? "CRITICAL"
          : "SCANNING";

  const healthLabelColor = healthScore >= 80
    ? "bg-emerald-900/50 text-emerald-400 border-emerald-400/20"
    : healthScore >= 50
      ? "bg-amber-900/50 text-amber-400 border-amber-400/20"
      : healthScore >= 0
        ? "bg-error-container text-md3-error border-md3-error/20"
        : "bg-surface-container-highest text-on-surface-variant border-outline-variant/20";

  // Top findings for the priority alerts
  const topFindings = useMemo(() => {
    return [...findings]
      .sort((a, b) => {
        const order = { critical: 0, warning: 1, info: 2, pass: 3 };
        return (order[a.severity] ?? 3) - (order[b.severity] ?? 3);
      })
      .slice(0, 4);
  }, [findings]);

  const findingBorderColor = (severity: string) => {
    switch (severity) {
      case "critical": return "border-md3-error";
      case "warning": return "border-md3-tertiary";
      default: return "border-md3-secondary";
    }
  };

  const findingBgColor = (severity: string) => {
    switch (severity) {
      case "critical": return "bg-error-container/20 hover:bg-error-container/30";
      case "warning": return "bg-surface-container hover:bg-surface-container-high";
      default: return "bg-surface-container hover:bg-surface-container-high";
    }
  };

  const findingTextColor = (severity: string) => {
    switch (severity) {
      case "critical": return "text-md3-error";
      case "warning": return "text-md3-tertiary";
      default: return "text-md3-secondary";
    }
  };

  return (
    <div className="relative min-h-screen overflow-x-hidden selection:bg-primary-container/30">
      {/* Background Elements */}
      <div className="fixed inset-0 obsidian-grid pointer-events-none" />
      <div className="fixed inset-0 pointer-events-none overflow-hidden">
        <div className="absolute top-[10%] left-[5%] w-64 h-64 bg-primary-container/10 rounded-full blur-[120px]" />
        <div className="absolute bottom-[20%] right-[10%] w-96 h-96 bg-tertiary-container/10 rounded-full blur-[150px]" />
        <div className="scanning-line" />
      </div>

      {/* Sidebar */}
      <aside className="fixed left-0 top-0 h-full w-64 bg-surface-container-lowest flex-col border-r border-surface-variant/20 z-40 hidden md:flex shadow-[40px_0_60px_-15px_rgba(0,0,0,0.5)]">
        <div className="p-6 flex items-center gap-3">
          <div className="w-8 h-8 flex items-center justify-center bg-primary-container rounded">
            <span
              className="material-symbols-outlined text-on-primary-container text-lg"
              style={{ fontVariationSettings: "'FILL' 1" }}
            >
              layers
            </span>
          </div>
          <div>
            <Link href="/" className="text-lg font-black text-primary-container font-[var(--font-headline-stack)] tracking-tighter hover:opacity-80 transition-opacity">
              Bundlescope
            </Link>
            <p className="text-[10px] text-on-surface-variant font-mono uppercase tracking-widest">
              {analysisId.slice(0, 8)}
            </p>
          </div>
        </div>

        <nav className="flex-1 mt-6 px-3 space-y-1">
          {sidebarNav.map((item) => (
            <button
              key={item.id}
              onClick={() => setActiveView(item.id)}
              className={`w-full px-4 py-3 flex items-center gap-3 transition-all text-left ${
                activeView === item.id
                  ? "bg-surface-container-high text-primary-container border-r-2 border-primary-container"
                  : "text-on-surface/60 hover:bg-surface hover:text-on-surface hover:translate-x-1"
              }`}
            >
              <span
                className="material-symbols-outlined"
                style={activeView === item.id && item.fill ? { fontVariationSettings: "'FILL' 1" } : undefined}
              >
                {item.icon}
              </span>
              <span className="text-xs font-medium font-[var(--font-headline-stack)] uppercase tracking-widest">
                {item.label}
              </span>
            </button>
          ))}
        </nav>

        <div className="p-4 mt-auto space-y-4">
          <div className="border-t border-outline-variant/20 pt-4 space-y-1">
            <Link
              href="/"
              className="text-on-surface/40 hover:text-on-surface px-4 py-2 flex items-center gap-3 text-xs font-[var(--font-headline-stack)] uppercase tracking-tighter"
            >
              <span className="material-symbols-outlined text-sm">arrow_back</span>
              Back to Upload
            </Link>
            {result?.cluster_version && (
              <div className="px-4 py-2 flex items-center gap-3 text-xs text-on-surface/40">
                <span className="material-symbols-outlined text-sm">info</span>
                <span className="font-mono text-[10px]">K8s {result.cluster_version}</span>
              </div>
            )}
          </div>
        </div>
      </aside>

      {/* Main Canvas */}
      <main className="md:ml-64 min-h-screen relative flex flex-col">
        {/* Top Bar */}
        <header className="flex justify-between items-center w-full px-6 py-3 bg-surface sticky top-0 z-50 border-b border-surface-variant/10">
          <h2 className="text-xl font-bold tracking-tighter text-primary-container font-[var(--font-headline-stack)]">
            {topTabs.find((t) => t.id === activeView)?.label ?? "Overview"}
          </h2>
          <div className="flex items-center gap-4">
            <div className="relative hidden sm:block">
              <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-on-surface-variant text-sm">
                search
              </span>
              <input
                className="bg-surface-container-lowest border border-outline-variant/10 pl-10 pr-4 py-1.5 text-[10px] font-mono w-64 focus:ring-1 focus:ring-primary-container focus:outline-none"
                placeholder="QUERY CLUSTER..."
                type="text"
              />
            </div>
            <button className="p-2 hover:bg-surface-container-high transition-all rounded-sm text-on-surface">
              <span className="material-symbols-outlined">notifications</span>
            </button>
          </div>
        </header>

        {/* Stream Status Banner */}
        {!isComplete && (
          <div className="px-6 lg:px-10 pt-6">
            <StreamStatus
              status={status}
              findingCount={findings.length}
              isComplete={isComplete}
              error={error}
            />
          </div>
        )}

        {/* ════════ OVERVIEW ════════ */}
        {activeView === "overview" && (
          <div className="p-6 lg:p-10 flex-1 grid grid-cols-12 gap-8 content-start">
            {/* Health Score Gauge */}
            <div className="col-span-12 lg:col-span-4 flex flex-col items-center justify-center space-y-3">
              <div className="relative w-48 h-48 flex items-center justify-center">
                <HealthScoreGauge score={healthScore} spinning={!isComplete} />
                <div className="absolute inset-0 flex flex-col items-center justify-center">
                  <span className="text-[10px] font-[var(--font-headline-stack)] uppercase tracking-[0.3em] text-on-surface-variant">
                    System Vital
                  </span>
                  <span className="text-5xl font-[var(--font-headline-stack)] font-black text-primary-container tracking-tighter">
                    {healthScore >= 0 ? healthScore : "—"}
                  </span>
                  <span className={`px-4 py-1 text-[10px] font-bold uppercase tracking-widest mt-2 border ${healthLabelColor}`}>
                    {healthLabel}
                  </span>
                </div>
              </div>
              <div className="text-center">
                <p className="text-on-surface-variant text-xs max-w-xs font-light leading-relaxed">
                  {result?.summary
                    ? result.summary.slice(0, 120) + (result.summary.length > 120 ? "..." : "")
                    : isStreaming
                      ? "Analysis in progress. Findings will appear as they are discovered."
                      : "Waiting for analysis results..."}
                </p>
              </div>
            </div>

            {/* Severity Donut + Priority Alerts */}
            <div className="col-span-12 lg:col-span-8 grid grid-cols-1 md:grid-cols-2 gap-8">
              {/* Severity Distribution — Horizontal Bars */}
              <div className="bg-surface-container-low p-6 border-l-2 border-primary-container">
                <h3 className="font-[var(--font-headline-stack)] text-xs uppercase tracking-widest text-on-surface-variant mb-6 flex items-center gap-2">
                  <span className="material-symbols-outlined text-sm">monitoring</span>
                  SEVERITY DISTRIBUTION
                </h3>
                <div className="space-y-5">
                  <SeverityBar label="Critical" count={severityCounts.critical} total={totalFindings} color="bg-red-500" textColor="text-red-400" />
                  <SeverityBar label="Warning" count={severityCounts.warning} total={totalFindings} color="bg-tertiary-container" textColor="text-md3-tertiary" />
                  <SeverityBar label="Info" count={severityCounts.info} total={totalFindings} color="bg-secondary-container" textColor="text-md3-secondary" />
                </div>
              </div>

              {/* High Priority Alerts */}
              <div className="space-y-3">
                <h3 className="font-[var(--font-headline-stack)] text-xs uppercase tracking-widest text-on-surface-variant mb-4 flex items-center gap-2">
                  <span className="material-symbols-outlined text-sm">priority_high</span>
                  HIGH PRIORITY ALERTS
                </h3>
                {topFindings.length === 0 ? (
                  <div className="text-center py-8 text-on-surface/30 text-sm">
                    {isStreaming ? "Discovering findings..." : "No findings yet"}
                  </div>
                ) : (
                  topFindings.map((f) => (
                    <div
                      key={f.id}
                      className={`group border-l-2 ${findingBorderColor(f.severity)} p-3 ${findingBgColor(f.severity)} transition-all cursor-pointer`}
                    >
                      <div className="flex justify-between items-start mb-1">
                        <span className={`text-[10px] font-mono ${findingTextColor(f.severity)}`}>
                          {f.category || f.severity.toUpperCase()}
                        </span>
                        <span className="text-[9px] text-on-surface-variant/50">
                          {f.source === "heuristic" ? "HEURISTIC" : "AI"}
                        </span>
                      </div>
                      <p className="text-xs font-medium">{f.title}</p>
                    </div>
                  ))
                )}
              </div>
            </div>


            {/* Root Cause Analysis */}
            {(result?.summary || result?.root_cause) && (
              <div className="col-span-12 glass-panel p-8 border border-outline-variant/20 relative overflow-hidden group">
                <div className="absolute top-0 right-0 p-4">
                  <span
                    className="material-symbols-outlined text-primary-container/20 text-6xl group-hover:scale-110 transition-transform"
                    style={{ fontVariationSettings: "'FILL' 1" }}
                  >
                    troubleshoot
                  </span>
                </div>
                <div className="relative z-10">
                  <h3 className="font-[var(--font-headline-stack)] text-2xl font-bold tracking-tight mb-6">
                    What We Found
                  </h3>

                  {/* Summary — the executive overview */}
                  {result.summary && (
                    <div className="mb-6">
                      <div className="flex items-center gap-2 mb-3">
                        <span className="material-symbols-outlined text-primary-container text-sm">summarize</span>
                        <span className="text-[10px] font-[var(--font-headline-stack)] text-primary-container uppercase font-bold tracking-widest">
                          Summary
                        </span>
                      </div>
                      <p className="text-base leading-relaxed text-on-surface/90">
                        {result.summary}
                      </p>
                    </div>
                  )}

                  {/* Issues — structured problem → solution list */}
                  {result.issues && result.issues.length > 0 && (
                    <div className="space-y-4">
                      {result.issues.map((issue, idx) => (
                        <div key={idx} className="bg-surface-container-lowest/60 p-5 rounded-lg border border-outline-variant/10">
                          <div className="flex items-start gap-3 mb-3">
                            <span className="material-symbols-outlined text-primary-container text-lg mt-0.5">error_outline</span>
                            <div>
                              <h4 className="font-[var(--font-headline-stack)] font-bold text-sm text-on-surface">
                                {issue.title}
                              </h4>
                              <p className="text-xs text-on-surface/60 mt-1 leading-relaxed">
                                {issue.description}
                              </p>
                              {issue.impact && (
                                <p className="text-xs text-md3-tertiary mt-1">
                                  Impact: {issue.impact}
                                </p>
                              )}
                            </div>
                          </div>
                          {issue.steps && issue.steps.length > 0 && (
                            <div className="ml-8 mt-3 space-y-2">
                              <span className="text-[10px] font-[var(--font-headline-stack)] text-emerald-400 uppercase font-bold tracking-widest">
                                How to fix
                              </span>
                              <ol className="space-y-1.5">
                                {issue.steps.map((step, stepIdx) => (
                                  <li key={stepIdx} className="flex items-start gap-2 text-xs text-on-surface/70 leading-relaxed">
                                    <span className="text-emerald-400 font-mono font-bold shrink-0">{stepIdx + 1}.</span>
                                    {step}
                                  </li>
                                ))}
                              </ol>
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Fallback: plain root_cause text if no structured issues */}
                  {(!result.issues || result.issues.length === 0) && result.root_cause && (
                    <div className="bg-surface-container-lowest/60 p-6 rounded-lg border border-outline-variant/10">
                      <p className="text-sm leading-relaxed text-on-surface/75 whitespace-pre-line">
                        {result.root_cause}
                      </p>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Bottom Data Grid */}
            <div className="col-span-12 grid grid-cols-1 md:grid-cols-3 gap-8 pb-12">
              <BottomStat
                label="Findings Total"
                value={findings.length > 0 ? `${findings.length} Issues` : "Scanning..."}
                color="text-md3-primary"
                progress={isComplete ? 1 : 0.5}
                barColor="bg-md3-primary"
              />
              <BottomStat
                label="Critical Issues"
                value={severityCounts.critical > 0 ? `${severityCounts.critical} Critical` : "None Detected"}
                color={severityCounts.critical > 0 ? "text-primary-container" : "text-emerald-400"}
                progress={findings.length > 0 ? severityCounts.critical / findings.length : 0}
                barColor={severityCounts.critical > 0 ? "bg-primary-container" : "bg-emerald-400"}
              />
              <BottomStat
                label="Analysis Status"
                value={isComplete ? "Analysis Complete" : isStreaming ? "In Progress" : "Starting..."}
                color="text-md3-secondary"
                progress={isComplete ? 1 : 0.6}
                barColor="bg-md3-secondary"
              />
            </div>
          </div>
        )}

        {/* ════════ FINDINGS ════════ */}
        {activeView === "findings" && (
          <div className="p-6 lg:p-10 flex-1 space-y-6">
            <div className="flex items-center gap-3">
              <span className="material-symbols-outlined text-on-surface/40 text-base">filter_list</span>
              <div className="flex gap-1">
                {(["all", "critical", "warning", "info"] as const).map((sev) => (
                  <button
                    key={sev}
                    onClick={() => setSeverityFilter(sev)}
                    className={`px-3 py-1.5 font-[var(--font-headline-stack)] text-[10px] font-bold uppercase tracking-wider transition-all ${
                      severityFilter === sev
                        ? "bg-surface-container-highest text-primary-container"
                        : "text-on-surface/40 hover:text-on-surface hover:bg-surface-container-high/50"
                    }`}
                  >
                    {sev === "all" ? "All" : sev.charAt(0).toUpperCase() + sev.slice(1)}
                    {sev !== "all" && (
                      <span className="ml-1 opacity-60">
                        {severityCounts[sev as keyof typeof severityCounts]}
                      </span>
                    )}
                  </button>
                ))}
              </div>
            </div>

            <ScrollArea className="h-[calc(100vh-220px)]">
              <div className="space-y-3 pr-4">
                {filteredFindings.length === 0 ? (
                  <div className="text-center py-12 text-on-surface/30 flex flex-col items-center gap-3">
                    <span className="material-symbols-outlined text-3xl">search_off</span>
                    {isStreaming
                      ? "Findings will appear here as they're discovered..."
                      : "No findings match the current filter"}
                  </div>
                ) : (
                  filteredFindings.map((finding) => (
                    <FindingCard key={finding.id} finding={finding} />
                  ))
                )}
              </div>
            </ScrollArea>
          </div>
        )}

        {/* ════════ TIMELINE ════════ */}
        {activeView === "timeline" && (
          <div className="p-6 lg:p-10 flex-1">
            <div className="bg-surface-container-low p-6 border-l-2 border-md3-tertiary">
              <h3 className="font-[var(--font-headline-stack)] text-xs uppercase tracking-widest text-on-surface-variant mb-6 flex items-center gap-2">
                <span className="material-symbols-outlined text-sm">schedule</span>
                Event Timeline
              </h3>
              <ScrollArea className="h-[calc(100vh-280px)]">
                <TimelineView events={result?.timeline_events ?? []} />
              </ScrollArea>
            </div>
          </div>
        )}

        {/* ════════ CHAT ════════ */}
        {activeView === "chat" && (
          <div className="p-6 lg:p-10 flex-1">
            <div className="glass-panel p-6 border border-outline-variant/20">
              <h3 className="font-[var(--font-headline-stack)] text-xs uppercase tracking-widest text-on-surface-variant mb-6 flex items-center gap-2">
                <span className="material-symbols-outlined text-sm">smart_toy</span>
                AI Investigation
              </h3>
              {isComplete ? (
                <ChatPanel analysisId={analysisId} />
              ) : (
                <div className="text-center py-12 text-on-surface/30 flex flex-col items-center gap-3">
                  <span className="material-symbols-outlined text-3xl animate-pulse">progress_activity</span>
                  Chat will be available once analysis is complete
                </div>
              )}
            </div>
          </div>
        )}
      </main>

      {/* Floating Action Button */}
      {isComplete && findings.length > 0 && (
        <div className="fixed bottom-8 right-8 z-50">
          <button
            onClick={() => setActiveView("findings")}
            className="flex items-center gap-3 bg-gradient-to-r from-primary-container to-inverse-primary p-4 rounded-xl shadow-[0_10px_30px_rgba(255,82,96,0.3)] hover:-translate-y-1 transition-all active:scale-95 text-on-primary-container"
          >
            <span
              className="material-symbols-outlined"
              style={{ fontVariationSettings: "'FILL' 1" }}
            >
              bolt
            </span>
            <span className="font-[var(--font-headline-stack)] text-xs font-bold uppercase tracking-widest">
              View All Findings
            </span>
          </button>
        </div>
      )}
    </div>
  );
}

/* ─── Sub-components ─── */

function HealthScoreGauge({ score, spinning = false }: { score: number; spinning?: boolean }) {
  const radius = 130;
  const circumference = 2 * Math.PI * radius;
  const pct = score >= 0 ? score / 100 : 0;
  const dashOffset = circumference - pct * circumference;

  const strokeColor = score >= 80
    ? "text-emerald-400"
    : score >= 50
      ? "text-amber-400"
      : "text-primary-container";

  return (
    <svg
      className={`w-full h-full -rotate-90 ${spinning ? "animate-[spin_3s_linear_infinite]" : ""}`}
      viewBox="0 0 288 288"
    >
      <circle
        className="text-surface-container-highest"
        cx="144" cy="144" r={radius}
        fill="transparent"
        stroke="currentColor"
        strokeWidth="8"
      />
      <circle
        className={`${strokeColor} transition-all duration-1000`}
        cx="144" cy="144" r={radius}
        fill="transparent"
        stroke="currentColor"
        strokeDasharray={circumference}
        strokeDashoffset={dashOffset}
        strokeWidth="12"
        strokeLinecap="round"
        style={{ filter: "drop-shadow(0 0 10px currentColor)" }}
      />
    </svg>
  );
}



function SeverityBar({
  label,
  count,
  total,
  color,
  textColor,
}: {
  label: string;
  count: number;
  total: number;
  color: string;
  textColor: string;
}) {
  const pct = total > 0 ? (count / total) * 100 : 0;
  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <span className={`text-[10px] font-[var(--font-headline-stack)] uppercase tracking-wider font-bold ${textColor}`}>
          {label}
        </span>
        <span className="font-mono text-xs text-on-surface/70">
          {count} <span className="text-on-surface/30">/ {total}</span>
        </span>
      </div>
      <div className="w-full h-2 bg-surface-container-highest rounded-full overflow-hidden">
        <div
          className={`h-full ${color} rounded-full transition-all duration-700`}
          style={{ width: `${Math.max(pct, count > 0 ? 4 : 0)}%` }}
        />
      </div>
    </div>
  );
}

function BottomStat({
  label,
  value,
  color,
  progress,
  barColor,
}: {
  label: string;
  value: string;
  color: string;
  progress: number;
  barColor: string;
}) {
  return (
    <div className="bg-surface-container-low p-6 flex flex-col justify-between h-40">
      <span className="text-[10px] font-[var(--font-headline-stack)] uppercase tracking-widest text-on-surface-variant">
        {label}
      </span>
      <div className={`text-3xl font-[var(--font-headline-stack)] font-bold ${color}`}>
        {value}
      </div>
      <div className="w-full h-1 bg-surface-container-highest mt-2 relative overflow-hidden">
        <div
          className={`absolute inset-y-0 left-0 ${barColor} transition-all duration-1000`}
          style={{ width: `${Math.max(progress * 100, 2)}%` }}
        />
      </div>
    </div>
  );
}
