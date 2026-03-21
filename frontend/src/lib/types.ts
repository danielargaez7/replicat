export type Severity = "critical" | "warning" | "info" | "pass";
export type Confidence = "high" | "medium" | "low";
export type FindingSource = "heuristic" | "ai_analysis" | "synthesis";

export interface Evidence {
  evidence_type: "log_line" | "event" | "config" | "status" | "resource";
  source_file: string;
  content: string;
  line_number?: number;
  resource_kind?: string;
  resource_name?: string;
}

export interface Finding {
  id: string;
  title: string;
  description: string;
  severity: Severity;
  confidence: Confidence;
  category: string;
  namespace?: string;
  resource_name?: string;
  resource_kind?: string;
  evidence: Evidence[];
  remediation?: string;
  source: FindingSource;
}

export interface TimelineEvent {
  timestamp: string;
  event_type: string;
  resource_kind: string;
  resource_name: string;
  namespace: string;
  message: string;
  severity: Severity;
}

export interface SynthesisIssue {
  title: string;
  description: string;
  impact: string;
  steps: string[];
}

export interface AnalysisResult {
  id: string;
  bundle_id: string;
  status: string;
  health_score: number;
  findings: Finding[];
  timeline_events: TimelineEvent[];
  summary?: string;
  root_cause?: string;
  issues?: SynthesisIssue[];
  cluster_version?: string;
  namespace_count: number;
  node_count: number;
  pod_count: number;
  pod_healthy_count: number;
  pod_failing_count: number;
  event_warning_count: number;
}

// ─── Remediation types ───

export type RiskLevel = "low" | "medium" | "high" | "critical";

export interface RemediationCommand {
  description: string;
  command: string;
  requires_sudo: boolean;
}

export interface RemediationItem {
  id: string;
  finding_id?: string;
  issue_index?: number;
  order: number;
  title: string;
  description: string;
  severity: Severity;
  risk_level: RiskLevel;
  estimated_downtime?: string;
  requires_approval: boolean;
  approved: boolean;
  auto_resolves: boolean;
  depends_on: string[];
  commands: RemediationCommand[];
  rollback_commands: RemediationCommand[];
  namespace?: string;
  resource_kind?: string;
  resource_name?: string;
  evidence_summary: string;
  original_remediation?: string;
}

export interface RemediationPlan {
  analysis_id: string;
  created_at: string;
  cluster_version?: string;
  summary?: string;
  root_cause?: string;
  health_score: number;
  items: RemediationItem[];
  total_items: number;
  critical_count: number;
  auto_resolve_count: number;
}

export interface AnalysisStatus {
  phase: string;
  message: string;
  progress?: string;
  file_count?: number;
}

export interface StreamEvent {
  type: "status" | "finding" | "complete" | "error";
  data: AnalysisStatus | Finding | AnalysisResult | { message: string };
}

export interface UploadResponse {
  analysis_id: string;
  filename: string;
  size_bytes: number;
}
