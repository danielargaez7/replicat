"""
Orchestrates the full analysis pipeline.
Yields (event_type, data) tuples for SSE streaming.
"""

from __future__ import annotations

from typing import AsyncGenerator

from models.bundle import ParsedBundle
from models.findings import AnalysisResult, Finding
from services.bundle_parser import parse_bundle
from services.heuristic import run_heuristic_pass


async def run_analysis_pipeline(
    analysis_id: str, bundle_path: str
) -> AsyncGenerator[tuple[str, dict | str], None]:

    yield ("status", {"phase": "extracting", "message": "Extracting bundle..."})

    try:
        parsed = await parse_bundle(analysis_id, bundle_path)
    except Exception as e:
        yield ("error", {"message": f"Failed to parse bundle: {e}"})
        return

    yield ("status", {
        "phase": "parsing_complete",
        "message": f"Parsed {len(parsed.pods)} pods, {len(parsed.events)} events, {len(parsed.log_files)} log files across {len(parsed.namespaces)} namespaces",
        "file_count": len(parsed.raw_file_tree),
    })

    # --- Pass 1: Heuristic Triage ---
    yield ("status", {"phase": "heuristic_pass", "message": "Running heuristic analysis..."})
    heuristic_findings = run_heuristic_pass(parsed)

    for finding in heuristic_findings:
        yield ("finding", finding.model_dump())

    yield ("status", {
        "phase": "heuristic_complete",
        "message": f"Heuristic pass found {len(heuristic_findings)} issues",
    })

    # --- Pass 2-4: AI Analysis ---
    all_findings = list(heuristic_findings)
    ai_findings: list[Finding] = []
    summary = None
    root_cause = None

    try:
        from services.ai_analyzer import run_ai_analysis, run_synthesis

        namespaces_with_issues = {f.namespace for f in heuristic_findings if f.namespace}
        if not namespaces_with_issues:
            namespaces_with_issues = set(parsed.namespaces[:5])

        total_ns = len(namespaces_with_issues)
        for i, ns in enumerate(namespaces_with_issues):
            yield ("status", {
                "phase": "ai_analysis",
                "message": f"AI analyzing namespace: {ns}",
                "progress": f"{i + 1}/{total_ns}",
            })

            ns_findings = await run_ai_analysis(parsed, ns, heuristic_findings)
            ai_findings.extend(ns_findings)
            for finding in ns_findings:
                yield ("finding", finding.model_dump())

        all_findings.extend(ai_findings)

        yield ("status", {"phase": "synthesis", "message": "Synthesizing root cause analysis..."})
        synthesis = await run_synthesis(parsed, all_findings)
        summary = synthesis.get("summary", "")
        root_cause = synthesis.get("root_cause", "")

    except Exception as e:
        yield ("status", {
            "phase": "ai_skipped",
            "message": f"AI analysis unavailable: {e}. Showing heuristic results only.",
        })

    # --- Build final result ---
    from services.heuristic import build_timeline_events, calculate_health_score

    health_score = calculate_health_score(all_findings)
    timeline = build_timeline_events(parsed)

    pod_failing = sum(
        1 for p in parsed.pods
        if p.phase not in ("Running", "Succeeded")
        or p.status_reason in ("CrashLoopBackOff", "ImagePullBackOff", "ErrImagePull", "OOMKilled", "Evicted")
        or any(not c.ready for c in p.containers)
    )
    warning_events = sum(1 for e in parsed.events if e.event_type == "Warning")
    cluster_ver = parsed.cluster_version.get("gitVersion", "unknown") if parsed.cluster_version else "unknown"

    result = AnalysisResult(
        id=analysis_id,
        bundle_id=analysis_id,
        status="complete",
        health_score=health_score,
        findings=all_findings,
        timeline_events=timeline,
        summary=summary,
        root_cause=root_cause,
        cluster_version=cluster_ver,
        namespace_count=len(parsed.namespaces),
        node_count=len(parsed.nodes),
        pod_count=len(parsed.pods),
        pod_healthy_count=len(parsed.pods) - pod_failing,
        pod_failing_count=pod_failing,
        event_warning_count=warning_events,
    )

    from routers.analysis import bundle_roots
    bundle_roots[analysis_id] = parsed.extraction_path

    yield ("status", {"phase": "complete", "message": "Analysis complete"})
    yield ("complete", result.model_dump())
