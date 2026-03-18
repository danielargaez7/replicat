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
      <div className="text-center py-12 text-muted-foreground">
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
              <div className="w-px flex-1 bg-border/50" />
            )}
          </div>

          {/* Content */}
          <div className="flex-1 pb-4 space-y-1">
            <div className="flex items-center gap-2 flex-wrap">
              <SeverityBadge severity={event.severity} showIcon={false} />
              <span className="text-xs text-muted-foreground font-mono">
                {formatTimestamp(event.timestamp)}
              </span>
            </div>
            <p className="text-sm">
              <span className="text-muted-foreground">
                {event.resource_kind}/{event.resource_name}
              </span>{" "}
              <span className="font-medium">{event.event_type}</span>
            </p>
            <p className="text-xs text-muted-foreground leading-relaxed">
              {event.message}
            </p>
            {event.namespace && (
              <span className="text-xs bg-muted px-1.5 py-0.5 rounded text-muted-foreground">
                {event.namespace}
              </span>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
