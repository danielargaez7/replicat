"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { ChevronDown, ChevronRight, Terminal, Wrench } from "lucide-react";
import { SeverityBadge } from "./SeverityBadge";
import type { Finding } from "@/lib/types";

export function FindingCard({ finding }: { finding: Finding }) {
  const [isOpen, setIsOpen] = useState(false);
  const hasDetails =
    (finding.evidence && finding.evidence.length > 0) || finding.remediation;

  return (
    <Card className="border-border/50 hover:border-border transition-colors">
      <Collapsible open={isOpen} onOpenChange={setIsOpen}>
        <CollapsibleTrigger
          className="w-full text-left"
          onClick={() => hasDetails && setIsOpen(!isOpen)}
        >
          <CardHeader className="cursor-pointer py-4 px-5">
            <div className="flex items-start gap-3">
              {hasDetails && (
                <div className="mt-0.5 text-muted-foreground">
                  {isOpen ? (
                    <ChevronDown className="h-4 w-4" />
                  ) : (
                    <ChevronRight className="h-4 w-4" />
                  )}
                </div>
              )}
              <div className="flex-1 space-y-1.5">
                <div className="flex items-center gap-2 flex-wrap">
                  <SeverityBadge severity={finding.severity} />
                  <span className="font-medium text-sm">{finding.title}</span>
                  <Badge
                    variant="outline"
                    className="text-xs text-muted-foreground"
                  >
                    {finding.source === "heuristic" ? "Heuristic" : "AI"}
                  </Badge>
                  {finding.confidence !== "high" && (
                    <Badge
                      variant="outline"
                      className="text-xs text-muted-foreground"
                    >
                      {finding.confidence} confidence
                    </Badge>
                  )}
                </div>
                <p className="text-sm text-muted-foreground leading-relaxed">
                  {finding.description}
                </p>
                {finding.namespace && (
                  <div className="flex gap-2 text-xs text-muted-foreground">
                    <span className="bg-muted px-1.5 py-0.5 rounded">
                      {finding.namespace}
                    </span>
                    {finding.resource_kind && finding.resource_name && (
                      <span className="bg-muted px-1.5 py-0.5 rounded">
                        {finding.resource_kind}/{finding.resource_name}
                      </span>
                    )}
                  </div>
                )}
              </div>
            </div>
          </CardHeader>
        </CollapsibleTrigger>

        {hasDetails && (
          <CollapsibleContent>
            <CardContent className="pt-0 pb-4 px-5 space-y-4">
              {finding.evidence.length > 0 && (
                <div className="space-y-2">
                  <div className="flex items-center gap-2 text-xs font-medium text-muted-foreground uppercase tracking-wider">
                    <Terminal className="h-3 w-3" />
                    Evidence
                  </div>
                  {finding.evidence.map((ev, i) => (
                    <div
                      key={i}
                      className="bg-muted/50 rounded-md p-3 font-mono text-xs leading-relaxed whitespace-pre-wrap overflow-x-auto border border-border/30"
                    >
                      {ev.source_file && (
                        <div className="text-muted-foreground mb-1">
                          {ev.source_file}
                          {ev.line_number && `:${ev.line_number}`}
                        </div>
                      )}
                      {ev.content}
                    </div>
                  ))}
                </div>
              )}

              {finding.remediation && (
                <div className="space-y-2">
                  <div className="flex items-center gap-2 text-xs font-medium text-muted-foreground uppercase tracking-wider">
                    <Wrench className="h-3 w-3" />
                    Remediation
                  </div>
                  <div className="bg-emerald-500/5 border border-emerald-500/20 rounded-md p-3 text-sm text-emerald-300 leading-relaxed">
                    {finding.remediation}
                  </div>
                </div>
              )}
            </CardContent>
          </CollapsibleContent>
        )}
      </Collapsible>
    </Card>
  );
}
