"use client";

import { useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import {
  Cpu,
  LayoutDashboard,
  List,
  Clock,
  ArrowLeft,
  Server,
  Box,
  AlertTriangle,
  Filter,
  MessageSquare,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { useAnalysisStream } from "@/lib/hooks/useAnalysisStream";
import { HealthScore } from "@/components/analysis/HealthScore";
import { FindingCard } from "@/components/analysis/FindingCard";
import { StreamStatus } from "@/components/analysis/StreamStatus";
import { TimelineView } from "@/components/analysis/TimelineView";
import { ChatPanel } from "@/components/analysis/ChatPanel";
import type { Finding, Severity } from "@/lib/types";

export default function AnalysisPage() {
  const params = useParams();
  const analysisId = params.id as string;
  const { status, findings, result, error, isStreaming, isComplete, startStream } =
    useAnalysisStream(analysisId);
  const [activeTab, setActiveTab] = useState("overview");
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

  return (
    <div className="min-h-screen flex flex-col">
      {/* Header */}
      <header className="border-b border-border/50 px-6 py-3">
        <div className="max-w-7xl mx-auto flex items-center gap-4">
          <Link href="/" className="text-muted-foreground hover:text-foreground transition-colors">
            <ArrowLeft className="h-4 w-4" />
          </Link>
          <div className="h-7 w-7 rounded-md bg-primary flex items-center justify-center">
            <Cpu className="h-3.5 w-3.5 text-primary-foreground" />
          </div>
          <span className="font-semibold text-sm">Bundlescope</span>
          <Separator orientation="vertical" className="h-5" />
          <span className="text-sm text-muted-foreground truncate">
            Analysis {analysisId.slice(0, 8)}...
          </span>
          {result?.cluster_version && (
            <Badge variant="outline" className="text-xs ml-auto">
              K8s {result.cluster_version}
            </Badge>
          )}
        </div>
      </header>

      <div className="flex-1 max-w-7xl mx-auto w-full px-6 py-6">
        {/* Stream Status */}
        <div className="mb-6">
          <StreamStatus
            status={status}
            findingCount={findings.length}
            isComplete={isComplete}
            error={error}
          />
        </div>

        {/* Tabs */}
        <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
          <TabsList className="bg-muted/50">
            <TabsTrigger value="overview" className="gap-1.5">
              <LayoutDashboard className="h-3.5 w-3.5" />
              Overview
            </TabsTrigger>
            <TabsTrigger value="findings" className="gap-1.5">
              <List className="h-3.5 w-3.5" />
              Findings
              {findings.length > 0 && (
                <Badge variant="secondary" className="ml-1 text-xs h-5 px-1.5">
                  {findings.length}
                </Badge>
              )}
            </TabsTrigger>
            <TabsTrigger value="timeline" className="gap-1.5">
              <Clock className="h-3.5 w-3.5" />
              Timeline
            </TabsTrigger>
            <TabsTrigger value="chat" className="gap-1.5" disabled={!isComplete}>
              <MessageSquare className="h-3.5 w-3.5" />
              Chat
            </TabsTrigger>
          </TabsList>

          {/* Overview Tab */}
          <TabsContent value="overview" className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {/* Health Score */}
              <Card className="border-border/50">
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium text-muted-foreground">
                    Cluster Health
                  </CardTitle>
                </CardHeader>
                <CardContent className="flex justify-center py-4">
                  {healthScore >= 0 ? (
                    <HealthScore score={healthScore} />
                  ) : (
                    <div className="text-muted-foreground text-sm">
                      Analyzing...
                    </div>
                  )}
                </CardContent>
              </Card>

              {/* Stats */}
              <Card className="border-border/50">
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium text-muted-foreground">
                    Cluster Stats
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-3 py-4">
                  <div className="flex items-center justify-between text-sm">
                    <div className="flex items-center gap-2 text-muted-foreground">
                      <Server className="h-4 w-4" />
                      Nodes
                    </div>
                    <span className="font-medium">{result?.node_count ?? "—"}</span>
                  </div>
                  <div className="flex items-center justify-between text-sm">
                    <div className="flex items-center gap-2 text-muted-foreground">
                      <Box className="h-4 w-4" />
                      Pods
                    </div>
                    <span className="font-medium">
                      {result ? (
                        <>
                          <span className="text-emerald-400">{result.pod_healthy_count}</span>
                          {" / "}
                          {result.pod_count}
                          {result.pod_failing_count > 0 && (
                            <span className="text-red-400 ml-1">
                              ({result.pod_failing_count} failing)
                            </span>
                          )}
                        </>
                      ) : (
                        "—"
                      )}
                    </span>
                  </div>
                  <div className="flex items-center justify-between text-sm">
                    <div className="flex items-center gap-2 text-muted-foreground">
                      <AlertTriangle className="h-4 w-4" />
                      Warning Events
                    </div>
                    <span className="font-medium">
                      {result?.event_warning_count ?? "—"}
                    </span>
                  </div>
                </CardContent>
              </Card>

              {/* Severity Breakdown */}
              <Card className="border-border/50">
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium text-muted-foreground">
                    Findings by Severity
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-3 py-4">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-red-400">Critical</span>
                    <span className="font-bold text-red-400">{severityCounts.critical}</span>
                  </div>
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-amber-400">Warning</span>
                    <span className="font-bold text-amber-400">{severityCounts.warning}</span>
                  </div>
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-blue-400">Info</span>
                    <span className="font-bold text-blue-400">{severityCounts.info}</span>
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Root Cause Summary */}
            {result?.summary && (
              <Card className="border-border/50">
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium text-muted-foreground">
                    Root Cause Analysis
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <p className="text-sm leading-relaxed">{result.summary}</p>
                  {result.root_cause && (
                    <div className="bg-muted/50 rounded-md p-4 text-sm leading-relaxed border border-border/30">
                      {result.root_cause}
                    </div>
                  )}
                </CardContent>
              </Card>
            )}

            {/* Top Findings Preview */}
            {findings.length > 0 && (
              <div className="space-y-3">
                <h3 className="text-sm font-medium text-muted-foreground">
                  Top Findings
                </h3>
                {findings
                  .filter((f) => f.severity === "critical" || f.severity === "warning")
                  .slice(0, 5)
                  .map((finding) => (
                    <FindingCard key={finding.id} finding={finding} />
                  ))}
              </div>
            )}
          </TabsContent>

          {/* Findings Tab */}
          <TabsContent value="findings" className="space-y-4">
            <div className="flex items-center gap-2">
              <Filter className="h-4 w-4 text-muted-foreground" />
              <div className="flex gap-1">
                {(["all", "critical", "warning", "info"] as const).map((sev) => (
                  <Button
                    key={sev}
                    variant={severityFilter === sev ? "default" : "ghost"}
                    size="sm"
                    className="text-xs h-7"
                    onClick={() => setSeverityFilter(sev)}
                  >
                    {sev === "all" ? "All" : sev.charAt(0).toUpperCase() + sev.slice(1)}
                    {sev !== "all" && (
                      <span className="ml-1 opacity-60">
                        {severityCounts[sev as keyof typeof severityCounts]}
                      </span>
                    )}
                  </Button>
                ))}
              </div>
            </div>

            <ScrollArea className="h-[calc(100vh-320px)]">
              <div className="space-y-3 pr-4">
                {filteredFindings.length === 0 ? (
                  <div className="text-center py-12 text-muted-foreground">
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
          </TabsContent>

          {/* Timeline Tab */}
          <TabsContent value="timeline">
            <Card className="border-border/50">
              <CardHeader>
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  Event Timeline
                </CardTitle>
              </CardHeader>
              <CardContent>
                <ScrollArea className="h-[calc(100vh-350px)]">
                  <TimelineView events={result?.timeline_events ?? []} />
                </ScrollArea>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Chat Tab */}
          <TabsContent value="chat">
            <Card className="border-border/50">
              <CardHeader>
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  Ask About This Bundle
                </CardTitle>
              </CardHeader>
              <CardContent>
                <ChatPanel analysisId={analysisId} />
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
