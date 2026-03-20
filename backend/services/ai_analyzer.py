"""
Passes 2-4: AI-powered deep analysis, synthesis, and remediation.

Uses targeted LLM calls with focused context windows per namespace.
"""

from __future__ import annotations

import json
import os
import uuid
from typing import Optional

from openai import AsyncOpenAI

from models.bundle import ParsedBundle
from models.findings import (
    Confidence,
    Evidence,
    EvidenceType,
    Finding,
    FindingSource,
    Severity,
)
from prompts.deep_analysis import SYSTEM_PROMPT, build_namespace_prompt
from prompts.synthesis import SYNTHESIS_SYSTEM_PROMPT, build_synthesis_prompt
from services.bundle_parser import extract_error_lines, read_log_file


def _get_client() -> AsyncOpenAI:
    return AsyncOpenAI(
        api_key=os.environ.get("OPENAI_API_KEY", ""),
        base_url=os.environ.get("OPENAI_BASE_URL"),
    )


def _get_model() -> str:
    return os.environ.get("OPENAI_MODEL", "gpt-4o")


def _build_pods_context(parsed: ParsedBundle, namespace: str) -> str:
    lines = []
    ns_pods = [p for p in parsed.pods if p.namespace == namespace]
    for pod in ns_pods[:20]:
        lines.append(f"Pod: {pod.name}")
        lines.append(f"  Phase: {pod.phase}, Reason: {pod.status_reason or 'N/A'}")
        lines.append(f"  Node: {pod.node_name or 'N/A'}")
        for c in pod.containers:
            lines.append(f"  Container: {c.name} | State: {c.state} | Restarts: {c.restart_count} | Exit: {c.exit_code} | Image: {c.image}")
            if c.reason:
                lines.append(f"    Reason: {c.reason}")
            if c.message:
                lines.append(f"    Message: {c.message[:200]}")
        lines.append("")
    return "\n".join(lines) if lines else "No pods found in this namespace."


def _build_events_context(parsed: ParsedBundle, namespace: str) -> str:
    lines = []
    ns_events = [e for e in parsed.events if e.namespace == namespace and e.event_type == "Warning"]
    ns_events.sort(key=lambda e: e.last_timestamp or e.first_timestamp or "", reverse=True)

    for event in ns_events[:30]:
        lines.append(f"[{event.reason}] {event.involved_object_kind}/{event.involved_object_name}: {event.message}")
        if event.count > 1:
            lines.append(f"  (occurred {event.count} times, last: {event.last_timestamp})")
    return "\n".join(lines) if lines else "No warning events in this namespace."


def _build_logs_context(parsed: ParsedBundle, namespace: str) -> str:
    lines = []
    ns_logs = [lf for lf in parsed.log_files if lf.namespace == namespace]

    for lf in ns_logs[:10]:
        errors = extract_error_lines(parsed.extraction_path, lf.path, context_lines=2)
        if errors:
            prev_tag = " (previous)" if lf.is_previous else ""
            lines.append(f"--- {lf.pod}/{lf.container}{prev_tag} ---")
            for err in errors[:5]:
                lines.append(f"  Line {err['line_number']}: {err['content'][:300]}")
            lines.append("")

    return "\n".join(lines) if lines else "No error patterns found in logs for this namespace."


def _build_services_context(parsed: ParsedBundle, namespace: str) -> str:
    lines = []
    ns_svcs = [s for s in parsed.services if s.namespace == namespace]
    for svc in ns_svcs[:15]:
        ports = ", ".join(f"{p.get('port', '?')}/{p.get('protocol', 'TCP')}" for p in svc.ports)
        selector = ", ".join(f"{k}={v}" for k, v in svc.selector.items())
        lines.append(f"Service: {svc.name} ({svc.service_type}) | Ports: {ports} | Selector: {selector}")
    return "\n".join(lines) if lines else "No services in this namespace."


def _build_heuristic_summary(findings: list[Finding], namespace: str) -> str:
    ns_findings = [f for f in findings if f.namespace == namespace]
    if not ns_findings:
        return "No heuristic findings for this namespace."

    lines = []
    for f in ns_findings:
        # Include confidence and transient/recovery info if present
        desc = f.description[:200]
        lines.append(f"- [{f.severity.value.upper()}] ({f.confidence.value} confidence) {f.title}: {desc}")
    return "\n".join(lines)


async def run_ai_analysis(
    parsed: ParsedBundle,
    namespace: str,
    heuristic_findings: list[Finding],
) -> list[Finding]:
    client = _get_client()
    model = _get_model()

    prompt = build_namespace_prompt(
        namespace=namespace,
        pods_data=_build_pods_context(parsed, namespace),
        events_data=_build_events_context(parsed, namespace),
        logs_data=_build_logs_context(parsed, namespace),
        services_data=_build_services_context(parsed, namespace),
        heuristic_summary=_build_heuristic_summary(heuristic_findings, namespace),
    )

    try:
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=4096,
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content or "[]"
        raw = json.loads(content)

        # Handle both direct array and wrapped response
        if isinstance(raw, dict):
            raw = raw.get("findings", raw.get("issues", [raw]))
        if not isinstance(raw, list):
            raw = [raw]

        findings = []
        for item in raw:
            if not isinstance(item, dict) or not item.get("title"):
                continue

            sev_str = item.get("severity", "info").lower()
            severity = {"critical": Severity.CRITICAL, "warning": Severity.WARNING}.get(sev_str, Severity.INFO)

            conf_str = item.get("confidence", "medium").lower()
            confidence = {"high": Confidence.HIGH, "low": Confidence.LOW}.get(conf_str, Confidence.MEDIUM)

            evidence = []
            if item.get("evidence_content"):
                evidence.append(Evidence(
                    evidence_type=EvidenceType.RESOURCE,
                    content=str(item["evidence_content"])[:500],
                    resource_kind=item.get("resource_kind", ""),
                    resource_name=item.get("resource_name", ""),
                ))

            findings.append(Finding(
                id=str(uuid.uuid4()),
                title=item["title"],
                description=item.get("description", ""),
                severity=severity,
                confidence=confidence,
                category=item.get("category", "ai-analysis"),
                namespace=namespace,
                resource_name=item.get("resource_name"),
                resource_kind=item.get("resource_kind"),
                evidence=evidence,
                remediation=item.get("remediation"),
                source=FindingSource.AI_ANALYSIS,
            ))

        return findings

    except Exception as e:
        return [Finding(
            id=str(uuid.uuid4()),
            title=f"AI analysis error for namespace {namespace}",
            description=f"AI analysis failed: {str(e)}",
            severity=Severity.INFO,
            confidence=Confidence.LOW,
            category="system",
            namespace=namespace,
            source=FindingSource.AI_ANALYSIS,
        )]


async def run_synthesis(
    parsed: ParsedBundle,
    all_findings: list[Finding],
) -> dict:
    client = _get_client()
    model = _get_model()

    findings_summary = "\n".join(
        f"[{f.severity.value.upper()}] ({f.source.value}, {f.confidence.value} confidence) "
        f"{f.title}: {f.description[:250]}"
        for f in all_findings
    )

    cluster_ver = parsed.cluster_version.get("gitVersion", "unknown") if parsed.cluster_version else "unknown"
    cluster_context = (
        f"Kubernetes version: {cluster_ver}\n"
        f"Namespaces: {len(parsed.namespaces)}\n"
        f"Nodes: {len(parsed.nodes)} (Ready: {sum(1 for n in parsed.nodes if n.ready)})\n"
        f"Pods: {len(parsed.pods)}\n"
        f"Total findings: {len(all_findings)}"
    )

    prompt = build_synthesis_prompt(findings_summary, cluster_context)

    try:
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYNTHESIS_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=2048,
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content or "{}"
        result = json.loads(content)

        return {
            "summary": result.get("summary", "Analysis complete."),
            "root_cause": result.get("root_cause", ""),
            "priority_order": result.get("priority_order", []),
            "correlated_groups": result.get("correlated_groups", []),
        }

    except Exception as e:
        return {
            "summary": f"Synthesis unavailable: {e}. Review individual findings for details.",
            "root_cause": "",
        }
