"""
Remediation Plan Builder

Transforms an AnalysisResult into a structured, ordered RemediationPlan.
Pure function — no DB calls, no async, no LLM calls.
Works with any existing analysis (backward compatible).
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone

from models.findings import AnalysisResult, Finding, Severity
from models.remediation import (
    RemediationCommand,
    RemediationItem,
    RemediationPlan,
    RiskLevel,
)

# ─── Command extraction ───

_BACKTICK_RE = re.compile(r"`([^`]+)`")
_NUMBERED_STEP_RE = re.compile(r"^\s*\d+[\.\)]\s*(.+)", re.MULTILINE)
_KUBECTL_RE = re.compile(r"(kubectl\s+[^\n`]+)")

# ─── Category ordering (lower = fix first) ───

_CATEGORY_PRIORITY: dict[str, int] = {
    "control-plane": 0,
    "etcd": 0,
    "node-health": 1,
    "scheduling": 2,
    "networking": 3,
    "storage": 4,
    "workload": 5,
    "pod-health": 5,
    "configuration": 6,
    "general": 7,
}

# ─── Downtime estimates by category ───

_DOWNTIME_ESTIMATES: dict[str, str] = {
    "control-plane": "5–15 minutes",
    "etcd": "5–15 minutes",
    "node-health": "10–30 minutes",
    "scheduling": "1–5 minutes",
    "networking": "1–5 minutes",
    "storage": "5–10 minutes",
    "workload": "< 2 minutes (rolling restart)",
    "pod-health": "< 1 minute",
    "configuration": "< 1 minute",
}


def build_remediation_plan(result: AnalysisResult) -> RemediationPlan:
    """Build an ordered remediation plan from an existing analysis result."""

    items: list[RemediationItem] = []
    seen_finding_ids: set[str] = set()

    # Step 1: Build items from synthesis issues (these are already prioritized by LLM)
    for idx, issue in enumerate(result.issues):
        if not issue.steps and not issue.title:
            continue

        commands = _extract_commands_from_steps(issue.steps)
        item = RemediationItem(
            id=str(uuid.uuid4()),
            issue_index=idx,
            order=0,  # assigned later
            title=issue.title,
            description=issue.description,
            severity=_infer_severity_from_impact(issue.impact),
            risk_level=_infer_risk_from_impact(issue.impact),
            estimated_downtime=None,
            requires_approval=False,
            commands=commands,
            evidence_summary=issue.impact,
            original_remediation="\n".join(issue.steps) if issue.steps else None,
        )
        items.append(item)

    # Step 2: Build items from individual findings (skip duplicates covered by synthesis)
    for finding in result.findings:
        if finding.severity == Severity.PASS:
            continue
        if not finding.remediation:
            continue

        seen_finding_ids.add(finding.id)
        commands = _extract_commands_from_text(finding.remediation)
        rollback = _infer_rollback(finding)

        item = RemediationItem(
            id=str(uuid.uuid4()),
            finding_id=finding.id,
            order=0,
            title=finding.title,
            description=finding.description,
            severity=finding.severity,
            risk_level=_severity_to_risk(finding.severity, finding.category),
            estimated_downtime=_DOWNTIME_ESTIMATES.get(finding.category or "", "Unknown"),
            requires_approval=finding.severity == Severity.CRITICAL,
            commands=commands,
            rollback_commands=rollback,
            namespace=finding.namespace,
            resource_kind=finding.resource_kind,
            resource_name=finding.resource_name,
            evidence_summary=_summarize_evidence(finding),
            original_remediation=finding.remediation,
        )
        items.append(item)

    # Step 3: Sort by priority
    items.sort(key=_sort_key)

    # Step 4: Assign order numbers and detect dependencies + auto-resolves
    _assign_ordering_and_dependencies(items)

    # Step 5: Build counts
    critical_count = sum(1 for i in items if i.severity == Severity.CRITICAL)
    auto_resolve_count = sum(1 for i in items if i.auto_resolves)

    return RemediationPlan(
        analysis_id=result.id,
        created_at=datetime.now(timezone.utc).isoformat(),
        cluster_version=result.cluster_version,
        summary=result.summary,
        root_cause=result.root_cause,
        health_score=result.health_score,
        items=items,
        total_items=len(items),
        critical_count=critical_count,
        auto_resolve_count=auto_resolve_count,
    )


# ─── Command extraction helpers ───


def _extract_commands_from_text(text: str) -> list[RemediationCommand]:
    """Extract kubectl commands from a remediation text string."""
    commands: list[RemediationCommand] = []
    seen: set[str] = set()

    # First try backtick-delimited commands
    for match in _BACKTICK_RE.finditer(text):
        cmd = match.group(1).strip()
        if cmd.startswith("kubectl") and cmd not in seen:
            seen.add(cmd)
            commands.append(RemediationCommand(command=cmd))

    # Then try raw kubectl commands
    if not commands:
        for match in _KUBECTL_RE.finditer(text):
            cmd = match.group(1).strip()
            if cmd not in seen:
                seen.add(cmd)
                commands.append(RemediationCommand(command=cmd))

    # If no commands found, treat the whole text as guidance
    if not commands and text.strip():
        commands.append(RemediationCommand(
            description=text.strip(),
            command="# Manual action required — see description above",
        ))

    return commands


def _extract_commands_from_steps(steps: list[str]) -> list[RemediationCommand]:
    """Extract commands from synthesis issue steps."""
    commands: list[RemediationCommand] = []

    for step in steps:
        step_commands = _extract_commands_from_text(step)
        if step_commands:
            # Attach the step text as description to the first command
            step_commands[0].description = step
            commands.extend(step_commands)
        elif step.strip():
            commands.append(RemediationCommand(
                description=step.strip(),
                command="# Manual action required — see description above",
            ))

    return commands


# ─── Risk / severity mapping ───


def _severity_to_risk(severity: Severity, category: str = "") -> RiskLevel:
    if category in ("control-plane", "etcd"):
        return RiskLevel.CRITICAL if severity == Severity.CRITICAL else RiskLevel.HIGH
    mapping = {
        Severity.CRITICAL: RiskLevel.HIGH,
        Severity.WARNING: RiskLevel.MEDIUM,
        Severity.INFO: RiskLevel.LOW,
        Severity.PASS: RiskLevel.LOW,
    }
    return mapping.get(severity, RiskLevel.MEDIUM)


def _infer_severity_from_impact(impact: str) -> Severity:
    lower = impact.lower()
    if any(w in lower for w in ("critical", "down", "outage", "unavailable", "crash")):
        return Severity.CRITICAL
    if any(w in lower for w in ("degraded", "slow", "failing", "error", "warning")):
        return Severity.WARNING
    return Severity.INFO


def _infer_risk_from_impact(impact: str) -> RiskLevel:
    severity = _infer_severity_from_impact(impact)
    return _severity_to_risk(severity)


# ─── Rollback inference ───


def _infer_rollback(finding: Finding) -> list[RemediationCommand]:
    """Infer rollback commands based on finding category and commands."""
    if not finding.remediation:
        return []

    # For resource limit changes, rollback is reverting the limit
    if "memory" in finding.remediation.lower() and "limits" in finding.remediation.lower():
        return [RemediationCommand(
            description="Revert memory limit to previous value",
            command="# Revert the memory limit change applied above",
        )]

    # For pod deletions or restarts
    if "delete pod" in finding.remediation.lower():
        return [RemediationCommand(
            description="Pod will be recreated by its controller — no rollback needed",
            command="# No rollback needed — controller will recreate the pod",
        )]

    return []


# ─── Evidence summarization ───


def _summarize_evidence(finding: Finding) -> str:
    if not finding.evidence:
        return finding.description[:200]

    parts = []
    for ev in finding.evidence[:3]:
        source = ev.source_file or ""
        content = ev.content[:150] if ev.content else ""
        if source and content:
            parts.append(f"{source}: {content}")
        elif content:
            parts.append(content)
    return " | ".join(parts) if parts else finding.description[:200]


# ─── Sorting and ordering ───


def _sort_key(item: RemediationItem) -> tuple:
    """Sort items: synthesis issues first, then by category priority, then severity."""
    is_synthesis = 0 if item.issue_index is not None else 1
    category_priority = 7  # default: general
    if item.finding_id:
        # We don't have the category directly on RemediationItem,
        # so we use the risk level as a proxy
        pass
    severity_order = {
        Severity.CRITICAL: 0,
        Severity.WARNING: 1,
        Severity.INFO: 2,
        Severity.PASS: 3,
    }
    return (is_synthesis, severity_order.get(item.severity, 3))


def _assign_ordering_and_dependencies(items: list[RemediationItem]) -> None:
    """Assign order numbers and detect auto-resolves."""
    # Build a map of resource -> item for dependency detection
    deployment_items: dict[str, RemediationItem] = {}

    for i, item in enumerate(items):
        item.order = i + 1

        # Track deployment-level items
        if item.resource_kind == "Deployment" and item.resource_name:
            key = f"{item.namespace or ''}:{item.resource_name}"
            deployment_items[key] = item

    # Second pass: mark pod items as auto-resolve if their deployment is being fixed
    for item in items:
        if item.resource_kind == "Pod" and item.resource_name and item.namespace:
            # Check if any deployment item matches this pod's namespace
            for dep_key, dep_item in deployment_items.items():
                dep_ns, dep_name = dep_key.split(":", 1)
                if dep_ns == item.namespace and item.resource_name.startswith(dep_name):
                    item.auto_resolves = True
                    item.depends_on = [dep_item.id]
                    break

    # Control-plane items are dependencies for everything else
    cp_ids = [i.id for i in items if i.severity == Severity.CRITICAL and i.order <= 2]
    if cp_ids:
        for item in items:
            if item.id not in cp_ids and not item.depends_on:
                item.depends_on = cp_ids
