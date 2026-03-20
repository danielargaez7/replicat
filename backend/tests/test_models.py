"""
Tests for Pydantic data models — ensure validation and serialization work correctly.
"""

import pytest
from pydantic import ValidationError

from models.findings import (
    AnalysisResult,
    Confidence,
    Evidence,
    EvidenceType,
    Finding,
    FindingSource,
    Severity,
    TimelineEvent,
)
from models.bundle import AnalysisStatus, BundleMetadata, PodInfo, ContainerStatus


class TestSeverityEnum:
    def test_all_values(self):
        assert Severity.CRITICAL.value == "critical"
        assert Severity.WARNING.value == "warning"
        assert Severity.INFO.value == "info"
        assert Severity.PASS.value == "pass"


class TestFinding:
    def test_minimal_finding(self):
        f = Finding(id="f-1", title="Test", description="Desc", severity=Severity.CRITICAL)
        assert f.id == "f-1"
        assert f.confidence == Confidence.HIGH  # default
        assert f.source == FindingSource.HEURISTIC  # default
        assert f.evidence == []

    def test_finding_with_evidence(self):
        ev = Evidence(
            evidence_type=EvidenceType.LOG_LINE,
            source_file="pod.log",
            content="OOMKilled",
            line_number=42,
        )
        f = Finding(
            id="f-2",
            title="OOM",
            description="Out of memory",
            severity=Severity.CRITICAL,
            evidence=[ev],
            remediation="Increase memory limits",
        )
        assert len(f.evidence) == 1
        assert f.evidence[0].line_number == 42
        assert f.remediation is not None

    def test_finding_serialization(self):
        f = Finding(id="f-3", title="T", description="D", severity=Severity.WARNING)
        d = f.model_dump()
        assert d["severity"] == "warning"
        assert d["confidence"] == "high"


class TestAnalysisResult:
    def test_defaults(self):
        r = AnalysisResult(id="a-1", bundle_id="b-1")
        assert r.health_score == 100
        assert r.findings == []
        assert r.pod_count == 0

    def test_full_result(self):
        r = AnalysisResult(
            id="a-2",
            bundle_id="b-2",
            status="complete",
            health_score=42,
            findings=[
                Finding(id="f-1", title="T", description="D", severity=Severity.CRITICAL),
            ],
            namespace_count=3,
            node_count=5,
            pod_count=20,
            pod_healthy_count=15,
            pod_failing_count=5,
        )
        assert r.health_score == 42
        assert len(r.findings) == 1
        assert r.pod_failing_count == 5


class TestAnalysisStatus:
    def test_workflow_states(self):
        states = [s.value for s in AnalysisStatus]
        assert "pending" in states
        assert "complete" in states
        assert "error" in states


class TestPodInfo:
    def test_pod_with_containers(self):
        pod = PodInfo(
            name="nginx-abc",
            namespace="default",
            phase="Running",
            containers=[
                ContainerStatus(name="nginx", ready=True, image="nginx:latest"),
                ContainerStatus(name="sidecar", ready=False, restart_count=5, exit_code=137),
            ],
        )
        assert len(pod.containers) == 2
        assert pod.containers[1].exit_code == 137


class TestTimelineEvent:
    def test_default_severity(self):
        ev = TimelineEvent(timestamp="2024-01-01T00:00:00Z", event_type="Warning")
        assert ev.severity == Severity.INFO  # default
