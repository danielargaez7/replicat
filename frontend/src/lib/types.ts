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

export interface AnalysisResult {
  id: string;
  bundle_id: string;
  status: string;
  health_score: number;
  findings: Finding[];
  timeline_events: TimelineEvent[];
  summary?: string;
  root_cause?: string;
  cluster_version?: string;
  namespace_count: number;
  node_count: number;
  pod_count: number;
  pod_healthy_count: number;
  pod_failing_count: number;
  event_warning_count: number;
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
