"""
Orchestrates the full analysis pipeline.
Yields (event_type, data) tuples for SSE streaming.

Optimizations:
- Parallel namespace analysis via asyncio.gather
- Streaming extraction (pipe mode tar)
- LLM response caching (skips API calls on cache hit)
- Model tiering (fast model for triage, full model for synthesis)
"""

from __future__ import annotations

import asyncio
import logging
from typing import AsyncGenerator

from database import AnalysisRecord, async_session
from models.bundle import AnalysisStatus
from models.findings import AnalysisResult, Finding
from services.bundle_parser import parse_bundle
from services.heuristic import run_heuristic_pass

logger = logging.getLogger("bundlescope")


async def _set_status(analysis_id: str, status: AnalysisStatus):
    async with async_session() as session:
        record = await session.get(AnalysisRecord, analysis_id)
        if record:
            record.status = status.value
            await session.commit()


async def run_analysis_pipeline(
    analysis_id: str, bundle_path: str
) -> AsyncGenerator[tuple[str, dict | str], None]:

    await _set_status(analysis_id, AnalysisStatus.EXTRACTING)
    yield ("status", {"phase": "extracting", "message": "Extracting bundle..."})

    try:
        parsed = await parse_bundle(analysis_id, bundle_path)
    except Exception as e:
        await _set_status(analysis_id, AnalysisStatus.ERROR)
        yield ("error", {"message": f"Failed to parse bundle: {e}"})
        return

    yield ("status", {
        "phase": "parsing_complete",
        "message": f"Parsed {len(parsed.pods)} pods, {len(parsed.events)} events, {len(parsed.log_files)} log files across {len(parsed.namespaces)} namespaces",
        "file_count": len(parsed.raw_file_tree),
    })

    # --- Pass 1: Heuristic Triage ---
    await _set_status(analysis_id, AnalysisStatus.HEURISTIC_PASS)
    yield ("status", {"phase": "heuristic_pass", "message": "Running heuristic analysis..."})
    heuristic_findings = run_heuristic_pass(parsed)

    # Stream heuristic findings immediately — fast time-to-first-result
    for finding in heuristic_findings:
        yield ("finding", finding.model_dump())

    yield ("status", {
        "phase": "heuristic_complete",
        "message": f"Heuristic pass found {len(heuristic_findings)} issues",
    })

    # --- Pass 2-4: AI Analysis ---
    await _set_status(analysis_id, AnalysisStatus.AI_ANALYSIS)
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
        ns_list = sorted(namespaces_with_issues)

        yield ("status", {
            "phase": "ai_analysis",
            "message": f"AI analyzing {total_ns} namespace(s) in parallel: {', '.join(ns_list[:5])}{'...' if total_ns > 5 else ''}",
            "progress": f"0/{total_ns}",
        })

        # Run all namespace analyses in parallel — uses asyncio.gather for speed
        # LLM cache hits return instantly; cache misses call the API
        tasks = [
            run_ai_analysis(parsed, ns, heuristic_findings)
            for ns in ns_list
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for i, (ns, result_or_exc) in enumerate(zip(ns_list, results)):
            if isinstance(result_or_exc, Exception):
                logger.error("AI analysis failed for %s: %s", ns, result_or_exc)
                yield ("status", {
                    "phase": "ai_analysis",
                    "message": f"AI analysis failed for {ns}: {result_or_exc}",
                    "progress": f"{i + 1}/{total_ns}",
                })
                continue

            ns_findings = result_or_exc
            ai_findings.extend(ns_findings)
            for finding in ns_findings:
                yield ("finding", finding.model_dump())

            yield ("status", {
                "phase": "ai_analysis",
                "message": f"Completed namespace: {ns}",
                "progress": f"{i + 1}/{total_ns}",
            })

        all_findings.extend(ai_findings)

        await _set_status(analysis_id, AnalysisStatus.SYNTHESIS)
        yield ("status", {"phase": "synthesis", "message": "Synthesizing root cause analysis..."})
        synthesis = await run_synthesis(parsed, all_findings)
        summary = synthesis.get("summary", "")
        root_cause = synthesis.get("root_cause", "")

    except Exception as e:
        logger.error("AI pipeline error: %s", e)
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

    # Batch write — single transaction for result + bundle root
    from database import AnalysisResultRecord, BundleRootRecord
    from cache import set_cached_result

    await _set_status(analysis_id, AnalysisStatus.COMPLETE)

    result_data = result.model_dump()
    async with async_session() as session:
        await session.merge(AnalysisResultRecord(
            id=analysis_id,
            bundle_id=analysis_id,
            result_data=result_data,
        ))
        await session.merge(BundleRootRecord(
            analysis_id=analysis_id,
            root_path=parsed.extraction_path,
        ))
        await session.commit()

    # Populate result cache
    await set_cached_result(analysis_id, result_data)

    yield ("status", {"phase": "complete", "message": "Analysis complete"})
    yield ("complete", result_data)
