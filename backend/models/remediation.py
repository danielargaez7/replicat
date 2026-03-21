from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel

from models.findings import Severity


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RemediationCommand(BaseModel):
    description: str = ""
    command: str


class RemediationItem(BaseModel):
    id: str
    finding_id: Optional[str] = None
    issue_index: Optional[int] = None
    order: int
    title: str
    description: str
    severity: Severity
    risk_level: RiskLevel
    estimated_downtime: Optional[str] = None
    requires_approval: bool = False
    approved: bool = False
    auto_resolves: bool = False
    depends_on: list[str] = []
    commands: list[RemediationCommand] = []
    rollback_commands: list[RemediationCommand] = []
    namespace: Optional[str] = None
    resource_kind: Optional[str] = None
    resource_name: Optional[str] = None
    evidence_summary: str = ""
    original_remediation: Optional[str] = None


class RemediationPlan(BaseModel):
    analysis_id: str
    created_at: str
    cluster_version: Optional[str] = None
    summary: Optional[str] = None
    root_cause: Optional[str] = None
    health_score: int = 100
    items: list[RemediationItem] = []
    total_items: int = 0
    critical_count: int = 0
    auto_resolve_count: int = 0
