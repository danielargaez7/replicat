"""
Passes 2-4: AI-powered deep analysis, synthesis, and remediation.

Uses targeted LLM calls with focused context windows per namespace.

Optimizations:
- Model tiering: cheap/fast model for per-namespace, expensive for synthesis
- LLM response caching by content hash (48h TTL)
- Token reduction: strips verbose/ephemeral fields from manifests
- Prompt structure optimized for OpenAI prompt caching (stable prefix)
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from typing import Optional

from openai import AsyncOpenAI

from cache import (
    build_llm_cache_key,
    build_synthesis_cache_key,
    get_cached_llm_response,
    get_cached_synthesis,
    set_cached_llm_response,
    set_cached_synthesis,
)
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

logger = logging.getLogger("bundlescope")

# ─── Model Tiering ───
# Fast/cheap model for per-namespace analysis (many calls)
# Full model for synthesis (one call, needs best reasoning)

def _get_client() -> AsyncOpenAI:
    return AsyncOpenAI(
        api_key=os.environ.get("OPENAI_API_KEY", ""),
        base_url=os.environ.get("OPENAI_BASE_URL"),
        timeout=30,
    )


def _get_triage_model() -> str:
    """Fast model for per-namespace analysis. 10-20x cheaper, 2-5x faster."""
    return os.environ.get("OPENAI_TRIAGE_MODEL", os.environ.get("OPENAI_MODEL", "gpt-4o-mini"))


def _get_synthesis_model() -> str:
    """Full model for synthesis — needs best reasoning capability."""
    return os.environ.get("OPENAI_SYNTHESIS_MODEL", os.environ.get("OPENAI_MODEL", "gpt-4o"))


# ─── Token Reduction ───
# Kubernetes manifests are extremely verbose. These fields add tokens
# without diagnostic value.

STRIP_KEYS = {
    "managedFields",
    "kubectl.kubernetes.io/last-applied-configuration",
    "deployment.kubernetes.io/revision",
    "field.cattle.io/publicEndpoints",
}

STRIP_METADATA_KEYS = {
    "uid", "resourceVersion", "generation", "selfLink",
    "creationTimestamp", "deletionTimestamp", "deletionGracePeriodSeconds",
    "ownerReferences", "finalizers", "managedFields",
}


def _strip_verbose_content(text: str, max_chars: int = 3000) -> str:
    """Strip known verbose/ephemeral patterns from text content to reduce tokens."""
    # Remove common high-token annotations line by line
    lines = []
    for line in text.splitlines():
        skip = False
        for key in STRIP_KEYS:
            if key in line:
                skip = True
                break
        if not skip:
            lines.append(line)

    result = "\n".join(lines)
    if len(result) > max_chars:
        # Keep first and last portions
        head = result[:max_chars // 2]
        tail = result[-(max_chars // 2):]
        result = head + f"\n... [{len(result) - max_chars} chars truncated] ...\n" + tail
    return result


# ─── Context Builders ───

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

    raw = "\n".join(lines) if lines else "No error patterns found in logs for this namespace."
    return _strip_verbose_content(raw)


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
        desc = f.description[:200]
        lines.append(f"- [{f.severity.value.upper()}] ({f.confidence.value} confidence) {f.title}: {desc}")
    return "\n".join(lines)


# ─── Per-Namespace Analysis (Pass 2) ───

async def run_ai_analysis(
    parsed: ParsedBundle,
    namespace: str,
    heuristic_findings: list[Finding],
) -> list[Finding]:
    client = _get_client()
    model = _get_triage_model()

    pods_data = _build_pods_context(parsed, namespace)
    events_data = _build_events_context(parsed, namespace)
    logs_data = _build_logs_context(parsed, namespace)
    services_data = _build_services_context(parsed, namespace)
    heuristic_summary = _build_heuristic_summary(heuristic_findings, namespace)

    prompt = build_namespace_prompt(
        namespace=namespace,
        pods_data=pods_data,
        events_data=events_data,
        logs_data=logs_data,
        services_data=services_data,
        heuristic_summary=heuristic_summary,
    )

    # ─── Check LLM cache first ───
    context_for_hash = f"{pods_data}{events_data}{logs_data}{services_data}{heuristic_summary}"
    cache_key = build_llm_cache_key(namespace, context_for_hash, model)
    cached = await get_cached_llm_response(cache_key)

    if cached:
        return _parse_llm_findings(cached, namespace)

    # ─── Call LLM ───
    try:
        response = await client.chat.completions.create(
            model=model,
            messages=[
                # System prompt FIRST and IDENTICAL across calls → enables OpenAI prompt caching
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=4096,
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content or '{"findings": []}'

        # Cache the raw response
        await set_cached_llm_response(cache_key, content)

        return _parse_llm_findings(content, namespace)

    except Exception as e:
        logger.error("AI analysis error for namespace %s: %s", namespace, e)
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


def _parse_llm_findings(content: str, namespace: str) -> list[Finding]:
    """Parse LLM JSON response into Finding objects."""
    try:
        raw = json.loads(content)
    except json.JSONDecodeError:
        return []

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


# ─── Synthesis (Pass 3-4) ───

async def run_synthesis(
    parsed: ParsedBundle,
    all_findings: list[Finding],
) -> dict:
    client = _get_client()
    model = _get_synthesis_model()

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

    # ─── Check synthesis cache ───
    synth_cache_key = build_synthesis_cache_key(findings_summary, model)
    cached = await get_cached_synthesis(synth_cache_key)
    if cached:
        try:
            result = json.loads(cached)
            return {
                "summary": result.get("summary", "Analysis complete."),
                "root_cause": result.get("root_cause", ""),
                "issues": result.get("issues", []),
            }
        except json.JSONDecodeError:
            pass

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

        # Cache the raw response
        await set_cached_synthesis(synth_cache_key, content)

        result = json.loads(content)

        return {
            "summary": result.get("summary", "Analysis complete."),
            "root_cause": result.get("root_cause", ""),
            "priority_order": result.get("priority_order", []),
            "correlated_groups": result.get("correlated_groups", []),
        }

    except Exception as e:
        logger.error("Synthesis error: %s", e)
        return {
            "summary": f"Synthesis unavailable: {e}. Review individual findings for details.",
            "root_cause": "",
        }
