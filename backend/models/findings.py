from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class Severity(str, Enum):
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"
    PASS = "pass"


class Confidence(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class FindingSource(str, Enum):
    HEURISTIC = "heuristic"
    AI_ANALYSIS = "ai_analysis"
    SYNTHESIS = "synthesis"


class EvidenceType(str, Enum):
    LOG_LINE = "log_line"
    EVENT = "event"
    CONFIG = "config"
    STATUS = "status"
    RESOURCE = "resource"


class Evidence(BaseModel):
    evidence_type: EvidenceType
    source_file: str = ""
    content: str = ""
    line_number: Optional[int] = None
    resource_kind: Optional[str] = None
    resource_name: Optional[str] = None


class Finding(BaseModel):
    id: str
    title: str
    description: str
    severity: Severity
    confidence: Confidence = Confidence.HIGH
    category: str = ""
    namespace: Optional[str] = None
    resource_name: Optional[str] = None
    resource_kind: Optional[str] = None
    evidence: list[Evidence] = []
    remediation: Optional[str] = None
    source: FindingSource = FindingSource.HEURISTIC


class TimelineEvent(BaseModel):
    timestamp: str
    event_type: str
    resource_kind: str = ""
    resource_name: str = ""
    namespace: str = ""
    message: str = ""
    severity: Severity = Severity.INFO


class SynthesisIssue(BaseModel):
    title: str = ""
    description: str = ""
    impact: str = ""
    steps: list[str] = []


class AnalysisResult(BaseModel):
    id: str
    bundle_id: str
    status: str = "pending"
    health_score: int = 100
    findings: list[Finding] = []
    timeline_events: list[TimelineEvent] = []
    summary: Optional[str] = None
    root_cause: Optional[str] = None
    issues: list[SynthesisIssue] = []
    cluster_version: Optional[str] = None
    namespace_count: int = 0
    node_count: int = 0
    pod_count: int = 0
    pod_healthy_count: int = 0
    pod_failing_count: int = 0
    event_warning_count: int = 0
