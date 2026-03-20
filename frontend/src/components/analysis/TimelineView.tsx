"use client";

import { SeverityBadge } from "./SeverityBadge";
import type { TimelineEvent } from "@/lib/types";

function severityLine(severity: string) {
  switch (severity) {
    case "critical":
      return "bg-red-400";
    case "warning":
      return "bg-amber-400";
    default:
      return "bg-blue-400";
  }
}

function formatTimestamp(ts: string) {
  try {
    const d = new Date(ts);
    return d.toLocaleString(undefined, {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  } catch {
    return ts;
  }
}

export function TimelineView({ events }: { events: TimelineEvent[] }) {
  if (events.length === 0) {
    return (
      <div className="text-center py-12 text-on-surface/30 flex flex-col items-center gap-3">
        <span className="material-symbols-outlined text-3xl">timeline</span>
        No timeline events to display
      </div>
    );
  }

  const sorted = [...events].sort(
    (a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
  );

  return (
    <div className="space-y-0">
      {sorted.map((event, i) => (
        <div key={i} className="flex gap-4 py-3">
          {/* Timeline line */}
          <div className="flex flex-col items-center w-6 shrink-0">
            <div className={`w-2.5 h-2.5 rounded-full ${severityLine(event.severity)} shrink-0`} />
            {i < sorted.length - 1 && (
              <div className="w-px flex-1 bg-outline-variant/20" />
            )}
          </div>

          {/* Content */}
          <div className="flex-1 pb-4 space-y-1.5">
            <div className="flex items-center gap-2 flex-wrap">
              <SeverityBadge severity={event.severity} showIcon={false} />
              <span className="text-[10px] text-on-surface/30 font-mono tracking-wider">
                {formatTimestamp(event.timestamp)}
              </span>
            </div>
            <p className="text-sm">
              <span className="text-on-surface/40">
                {event.resource_kind}/{event.resource_name}
              </span>{" "}
              <span className="font-bold font-[var(--font-headline-stack)] uppercase tracking-tight text-on-surface">
                {event.event_type}
              </span>
            </p>
            <p className="text-xs text-on-surface/40 leading-relaxed">
              {event.message}
            </p>
            {event.namespace && (
              <span className="text-[10px] bg-surface-container-highest/60 text-on-surface/30 px-2 py-0.5 rounded-md font-mono">
                {event.namespace}
              </span>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
