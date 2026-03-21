"""
Pass 1: Heuristic Triage

Deterministic pattern detection for known Kubernetes failure modes.
No AI calls — fast, reliable, evidence-grounded.
"""

from __future__ import annotations

import re
import uuid
from typing import Optional

from models.bundle import (
    EventInfo,
    NodeInfo,
    ParsedBundle,
    PodInfo,
)
from models.findings import (
    Confidence,
    Evidence,
    EvidenceType,
    Finding,
    FindingSource,
    Severity,
    TimelineEvent,
)
from services.bundle_parser import extract_error_lines, read_log_file

EXIT_CODE_MAP = {
    137: ("OOMKilled or SIGKILL", Severity.CRITICAL),
    139: ("Segmentation fault (SIGSEGV)", Severity.CRITICAL),
    1: ("Application error", Severity.WARNING),
    2: ("Shell misuse or missing command", Severity.WARNING),
    126: ("Permission denied or not executable", Severity.WARNING),
    127: ("Command not found", Severity.WARNING),
    128: ("Invalid exit argument", Severity.WARNING),
    143: ("SIGTERM (graceful shutdown)", Severity.INFO),
}

POD_STATUS_RULES: dict[str, tuple[Severity, str, str]] = {
    "CrashLoopBackOff": (
        Severity.CRITICAL,
        "Pod is crash-looping",
        "Check container logs with `kubectl logs {pod} -n {ns} --previous`. Common causes: missing env vars, bad entrypoint, config errors.",
    ),
    "ImagePullBackOff": (
        Severity.CRITICAL,
        "Container image cannot be pulled",
        "Verify image name and tag. Check registry access. Run `kubectl describe pod {pod} -n {ns}` for pull error details.",
    ),
    "ErrImagePull": (
        Severity.CRITICAL,
        "Container image pull failed",
        "Verify the image exists and is accessible. Check image pull secrets if using a private registry.",
    ),
    "OOMKilled": (
        Severity.CRITICAL,
        "Container killed due to memory limit",
        "Increase memory limits in the pod spec. Current limit may be too low for the workload.",
    ),
    "CreateContainerConfigError": (
        Severity.CRITICAL,
        "Container configuration error",
        "Check for missing ConfigMaps, Secrets, or malformed environment variable references.",
    ),
    "RunContainerError": (
        Severity.CRITICAL,
        "Container failed to start",
        "Check security context, volume mounts, and resource constraints.",
    ),
    "Pending": (
        Severity.WARNING,
        "Pod stuck in Pending state",
        "Check node resources with `kubectl describe nodes`. Look for taints, insufficient CPU/memory, or missing PVCs.",
    ),
    "Evicted": (
        Severity.WARNING,
        "Pod was evicted from the node",
        "Usually caused by node resource pressure (disk, memory). Check node conditions.",
    ),
    "Unknown": (
        Severity.WARNING,
        "Pod in Unknown state",
        "Node may be unreachable. Check node status and network connectivity.",
    ),
}

# Patterns for control plane log analysis
ETCD_ERROR_PATTERNS = [
    re.compile(r"etcd.*connection\s+(refused|error|failed|reset)", re.IGNORECASE),
    re.compile(r"etcd.*transport.*closing", re.IGNORECASE),
    re.compile(r"etcd.*dial\s+tcp.*connection\s+refused", re.IGNORECASE),
    re.compile(r"etcd.*authentication\s+handshake\s+failed", re.IGNORECASE),
    re.compile(r"etcd.*context\s+(deadline\s+exceeded|canceled)", re.IGNORECASE),
    re.compile(r"grpc.*transport.*closing", re.IGNORECASE),
    re.compile(r"operation\s+was\s+canceled", re.IGNORECASE),
    re.compile(r"failed\s+to\s+(list|watch|get).*etcd", re.IGNORECASE),
]

RBAC_ERROR_PATTERN = re.compile(
    r"(forbidden|unauthorized|cannot\s+(list|watch|get|create|update|delete|patch).*"
    r"(clusterrole|role|rolebinding|clusterrolebinding|RBAC)?"
    r"|Failed\s+to\s+watch\s+\*v\d+\."
    r"|User\s+\"system:.*\"\s+cannot)",
    re.IGNORECASE,
)

LEADER_ELECTION_SUCCESS = re.compile(
    r"(successfully\s+acquired\s+lease|became\s+leader|leading)", re.IGNORECASE
)

CACHE_SYNC_SUCCESS = re.compile(
    r"(caches\s+(are\s+)?synced|cache\s+sync\s+complete)", re.IGNORECASE
)

CONTROL_PLANE_COMPONENTS = {
    "kube-apiserver", "kube-scheduler", "kube-controller-manager",
    "etcd", "kube-proxy", "coredns",
}


def run_heuristic_pass(parsed: ParsedBundle) -> list[Finding]:
    findings: list[Finding] = []

    findings.extend(_check_pod_statuses(parsed))
    findings.extend(_check_container_exit_codes(parsed))
    findings.extend(_check_events(parsed))
    findings.extend(_check_nodes(parsed))
    findings.extend(_check_deployments(parsed))
    findings.extend(_check_control_plane_logs(parsed))
    findings.extend(_check_log_errors(parsed))

    return findings


def _make_finding(
    title: str,
    description: str,
    severity: Severity,
    namespace: Optional[str] = None,
    resource_name: Optional[str] = None,
    resource_kind: Optional[str] = None,
    evidence: Optional[list[Evidence]] = None,
    remediation: Optional[str] = None,
    category: str = "general",
    confidence: Confidence = Confidence.HIGH,
) -> Finding:
    return Finding(
        id=str(uuid.uuid4()),
        title=title,
        description=description,
        severity=severity,
        confidence=confidence,
        category=category,
        namespace=namespace,
        resource_name=resource_name,
        resource_kind=resource_kind,
        evidence=evidence or [],
        remediation=remediation,
        source=FindingSource.HEURISTIC,
    )


def _check_pod_statuses(parsed: ParsedBundle) -> list[Finding]:
    findings = []
    for pod in parsed.pods:
        reasons_checked = set()

        # Check pod phase
        if pod.phase in ("Failed", "Unknown"):
            reason = pod.status_reason or pod.phase
            if reason in POD_STATUS_RULES:
                sev, desc, remed = POD_STATUS_RULES[reason]
                remed = remed.format(pod=pod.name, ns=pod.namespace)
                findings.append(_make_finding(
                    title=f"{reason}: {pod.name}",
                    description=f"{desc}. Pod `{pod.name}` in namespace `{pod.namespace}` is in {pod.phase} phase with reason: {reason}.",
                    severity=sev,
                    namespace=pod.namespace,
                    resource_name=pod.name,
                    resource_kind="Pod",
                    evidence=[Evidence(
                        evidence_type=EvidenceType.STATUS,
                        content=f"Phase: {pod.phase}, Reason: {reason}",
                        resource_kind="Pod",
                        resource_name=pod.name,
                    )],
                    remediation=remed,
                    category="pod-health",
                ))
                reasons_checked.add(reason)

        # Check container-level waiting reasons
        if pod.status_reason and pod.status_reason not in reasons_checked:
            reason = pod.status_reason
            if reason in POD_STATUS_RULES:
                sev, desc, remed = POD_STATUS_RULES[reason]
                remed = remed.format(pod=pod.name, ns=pod.namespace)
                findings.append(_make_finding(
                    title=f"{reason}: {pod.name}",
                    description=f"{desc}. Pod `{pod.name}` in namespace `{pod.namespace}`.",
                    severity=sev,
                    namespace=pod.namespace,
                    resource_name=pod.name,
                    resource_kind="Pod",
                    evidence=[Evidence(
                        evidence_type=EvidenceType.STATUS,
                        content=f"Phase: {pod.phase}, Status: {reason}",
                        resource_kind="Pod",
                        resource_name=pod.name,
                    )],
                    remediation=remed,
                    category="pod-health",
                ))

        # High restart count
        for container in pod.containers:
            if container.restart_count >= 5:
                findings.append(_make_finding(
                    title=f"High restart count: {pod.name}/{container.name}",
                    description=f"Container `{container.name}` in pod `{pod.name}` has restarted {container.restart_count} times.",
                    severity=Severity.WARNING,
                    namespace=pod.namespace,
                    resource_name=pod.name,
                    resource_kind="Pod",
                    evidence=[Evidence(
                        evidence_type=EvidenceType.STATUS,
                        content=f"Container: {container.name}, Restarts: {container.restart_count}, State: {container.state}",
                        resource_kind="Pod",
                        resource_name=pod.name,
                    )],
                    remediation="Investigate container logs for crash reasons. Check liveness/readiness probes.",
                    category="pod-health",
                ))

    return findings


def _check_container_exit_codes(parsed: ParsedBundle) -> list[Finding]:
    findings = []
    for pod in parsed.pods:
        for container in pod.containers:
            if container.exit_code is not None and container.exit_code != 0:
                code = container.exit_code
                desc_suffix, severity = EXIT_CODE_MAP.get(code, (f"Exit code {code}", Severity.WARNING))

                detail = f"Container `{container.name}` in pod `{pod.name}` exited with code {code} ({desc_suffix})."
                if container.message:
                    detail += f" Message: {container.message}"

                remed = None
                if code == 137:
                    remed = "Container was OOMKilled or received SIGKILL. Check memory limits and actual usage. Consider increasing `resources.limits.memory`."
                elif code == 139:
                    remed = "Segmentation fault in the container process. This is typically a bug in the application code."
                elif code == 1:
                    remed = "Application exited with an error. Check container logs for details."

                findings.append(_make_finding(
                    title=f"Exit code {code}: {pod.name}/{container.name}",
                    description=detail,
                    severity=severity,
                    namespace=pod.namespace,
                    resource_name=pod.name,
                    resource_kind="Pod",
                    evidence=[Evidence(
                        evidence_type=EvidenceType.STATUS,
                        content=f"Exit code: {code} ({desc_suffix}), Reason: {container.reason or 'N/A'}, Message: {container.message or 'N/A'}",
                        resource_kind="Pod",
                        resource_name=pod.name,
                    )],
                    remediation=remed,
                    category="container-exit",
                ))
    return findings


def _check_events(parsed: ParsedBundle) -> list[Finding]:
    findings = []
    IMPORTANT_REASONS = {
        "FailedScheduling": (Severity.WARNING, "scheduling"),
        "FailedMount": (Severity.WARNING, "storage"),
        "FailedAttachVolume": (Severity.WARNING, "storage"),
        "Unhealthy": (Severity.WARNING, "probe-health"),
        "BackOff": (Severity.WARNING, "pod-health"),
        "FailedCreate": (Severity.WARNING, "workload"),
        "EvictionThresholdMet": (Severity.WARNING, "node-health"),
        "NodeNotReady": (Severity.CRITICAL, "node-health"),
        "OOMKilling": (Severity.CRITICAL, "resource-limits"),
        "SystemOOM": (Severity.CRITICAL, "node-health"),
        "Killing": (Severity.INFO, "pod-lifecycle"),
        "Pulled": (Severity.INFO, "pod-lifecycle"),
    }

    for event in parsed.events:
        if event.event_type != "Warning":
            continue

        severity = Severity.WARNING
        category = "events"

        if event.reason in IMPORTANT_REASONS:
            severity, category = IMPORTANT_REASONS[event.reason]

        title = f"{event.reason}: {event.involved_object_kind}/{event.involved_object_name}"
        desc = event.message
        if event.count > 1:
            desc += f" (occurred {event.count} times)"

        findings.append(_make_finding(
            title=title,
            description=desc,
            severity=severity,
            namespace=event.namespace,
            resource_name=event.involved_object_name,
            resource_kind=event.involved_object_kind,
            evidence=[Evidence(
                evidence_type=EvidenceType.EVENT,
                content=f"Reason: {event.reason}, Message: {event.message}",
                resource_kind=event.involved_object_kind,
                resource_name=event.involved_object_name,
            )],
            category=category,
            confidence=Confidence.HIGH,
        ))
    return findings


def _check_nodes(parsed: ParsedBundle) -> list[Finding]:
    findings = []
    PRESSURE_CONDITIONS = {"MemoryPressure", "DiskPressure", "PIDPressure", "NetworkUnavailable"}

    for node in parsed.nodes:
        if not node.ready:
            findings.append(_make_finding(
                title=f"Node NotReady: {node.name}",
                description=f"Node `{node.name}` is not in Ready state. Pods on this node may be disrupted.",
                severity=Severity.CRITICAL,
                resource_name=node.name,
                resource_kind="Node",
                evidence=[Evidence(
                    evidence_type=EvidenceType.STATUS,
                    content=f"Node: {node.name}, Ready: False, Kubelet: {node.kubelet_version or 'unknown'}",
                    resource_kind="Node",
                    resource_name=node.name,
                )],
                remediation="Check kubelet status on the node. Verify network connectivity. Run `kubectl describe node` for conditions.",
                category="node-health",
            ))

        for cond in node.conditions:
            ctype = cond.get("type", "")
            if ctype in PRESSURE_CONDITIONS and cond.get("status") == "True":
                findings.append(_make_finding(
                    title=f"{ctype}: {node.name}",
                    description=f"Node `{node.name}` is under {ctype}. This can cause pod evictions and scheduling failures.",
                    severity=Severity.WARNING,
                    resource_name=node.name,
                    resource_kind="Node",
                    evidence=[Evidence(
                        evidence_type=EvidenceType.STATUS,
                        content=f"Condition: {ctype}=True, Message: {cond.get('message', 'N/A')}",
                        resource_kind="Node",
                        resource_name=node.name,
                    )],
                    remediation=f"Investigate {ctype} on node `{node.name}`. Free up resources or add capacity.",
                    category="node-health",
                ))

    return findings


def _check_deployments(parsed: ParsedBundle) -> list[Finding]:
    findings = []
    for dep in parsed.deployments:
        if dep.replicas > 0 and dep.unavailable_replicas > 0:
            findings.append(_make_finding(
                title=f"Deployment degraded: {dep.name}",
                description=f"Deployment `{dep.name}` in `{dep.namespace}` has {dep.unavailable_replicas} unavailable replicas out of {dep.replicas} desired.",
                severity=Severity.WARNING if dep.available_replicas > 0 else Severity.CRITICAL,
                namespace=dep.namespace,
                resource_name=dep.name,
                resource_kind="Deployment",
                evidence=[Evidence(
                    evidence_type=EvidenceType.STATUS,
                    content=f"Desired: {dep.replicas}, Ready: {dep.ready_replicas}, Available: {dep.available_replicas}, Unavailable: {dep.unavailable_replicas}",
                    resource_kind="Deployment",
                    resource_name=dep.name,
                )],
                remediation="Check pod status for this deployment. Run `kubectl rollout status deployment/{name} -n {ns}`".format(
                    name=dep.name, ns=dep.namespace
                ),
                category="workload",
            ))

        if dep.replicas > 0 and dep.ready_replicas == 0:
            findings.append(_make_finding(
                title=f"Deployment has zero ready replicas: {dep.name}",
                description=f"Deployment `{dep.name}` in `{dep.namespace}` has 0/{dep.replicas} ready replicas. The service is likely down.",
                severity=Severity.CRITICAL,
                namespace=dep.namespace,
                resource_name=dep.name,
                resource_kind="Deployment",
                evidence=[Evidence(
                    evidence_type=EvidenceType.STATUS,
                    content=f"Desired: {dep.replicas}, Ready: 0",
                    resource_kind="Deployment",
                    resource_name=dep.name,
                )],
                remediation=f"Check pods owned by deployment `{dep.name}`. Look for CrashLoopBackOff, image pull errors, or scheduling issues.",
                category="workload",
            ))
    return findings


def _check_control_plane_logs(parsed: ParsedBundle) -> list[Finding]:
    """
    Analyze control plane component logs for:
    - etcd connectivity/TLS failures (CRITICAL infrastructure)
    - RBAC permission errors (with transient vs persistent distinction)
    - Leader election status (recovery signal)
    """
    findings = []

    for lf in parsed.log_files:
        if lf.size_bytes == 0:
            continue

        # Only check control plane components
        component_name = None
        for cp in CONTROL_PLANE_COMPONENTS:
            if cp in lf.pod.lower() or cp in lf.container.lower():
                component_name = cp
                break
        if not component_name:
            continue

        log_content = read_log_file(parsed.extraction_path, lf.path, max_lines=2000)
        if not log_content:
            continue

        log_lines = log_content.splitlines()

        # ─── etcd connectivity failures ───
        if component_name in ("kube-apiserver", "etcd"):
            etcd_errors = []
            for i, line in enumerate(log_lines):
                for pattern in ETCD_ERROR_PATTERNS:
                    if pattern.search(line):
                        etcd_errors.append((i + 1, line.strip()))
                        break
                if len(etcd_errors) >= 30:
                    break

            if len(etcd_errors) >= 5:
                # Check recovery signals — if the apiserver started serving or etcd
                # elected a leader, these errors are transient startup race conditions
                serving_pattern = re.compile(
                    r"Serving (securely|insecure) on", re.IGNORECASE
                )
                has_serving = any(serving_pattern.search(line) for line in log_lines)
                has_leader = any(LEADER_ELECTION_SUCCESS.search(line) for line in log_lines)
                recovered = has_serving or has_leader

                if recovered:
                    severity = Severity.WARNING
                    confidence = Confidence.MEDIUM
                    transient_note = (
                        " However, recovery signals were detected (the API server started serving "
                        "or etcd elected a leader), indicating these are transient startup race "
                        "conditions rather than a persistent outage."
                    )
                else:
                    severity = Severity.CRITICAL
                    confidence = Confidence.HIGH
                    transient_note = ""

                sample = etcd_errors[:5]
                evidence_text = "\n".join(f"Line {num}: {text[:200]}" for num, text in sample)

                findings.append(_make_finding(
                    title=f"etcd connectivity errors in {component_name}{' (transient)' if recovered else ''}",
                    description=(
                        f"Detected {len(etcd_errors)} etcd connection error(s) in `{component_name}` logs."
                        f"{transient_note if recovered else ' The API server cannot reliably communicate with etcd, which prevents reading and writing cluster state. This is a critical infrastructure issue that affects all cluster operations.'}"
                    ),
                    severity=severity,
                    namespace="kube-system",
                    resource_name=lf.pod,
                    resource_kind="Pod",
                    evidence=[Evidence(
                        evidence_type=EvidenceType.LOG_LINE,
                        source_file=lf.path,
                        content=evidence_text,
                    )],
                    remediation=(
                        "1. Check etcd pod health: `kubectl get pods -n kube-system -l component=etcd`\n"
                        "2. Verify etcd endpoints: `kubectl get endpoints -n kube-system etcd`\n"
                        "3. Check etcd TLS certificates for expiry: `openssl x509 -in /etc/kubernetes/pki/etcd/server.crt -noout -dates`\n"
                        "4. Review etcd logs: `kubectl logs -n kube-system etcd-<node> --tail=100`\n"
                        "5. If TLS handshake failures: regenerate etcd certificates with `kubeadm init phase certs etcd-server`"
                        + ("\n6. If errors are only at startup with recovery signals, no action needed." if recovered else "")
                    ),
                    category="control-plane",
                    confidence=confidence,
                ))

        # ─── RBAC / permission errors ───
        rbac_errors = []
        for i, line in enumerate(log_lines):
            if RBAC_ERROR_PATTERN.search(line):
                rbac_errors.append((i + 1, line.strip()))
            if len(rbac_errors) >= 30:
                break

        if rbac_errors:
            # Check for recovery signals — leader election success and cache sync
            has_leader = any(LEADER_ELECTION_SUCCESS.search(line) for line in log_lines)
            has_cache_sync = any(CACHE_SYNC_SUCCESS.search(line) for line in log_lines)
            recovered = has_leader or has_cache_sync

            # Determine if errors are transient (startup) or persistent
            # If we see recovery signals after RBAC errors, they're likely transient
            if recovered:
                severity = Severity.WARNING
                transient_note = (
                    " However, the component subsequently acquired its leader lease and synced caches, "
                    "indicating these errors are likely transient startup race conditions rather than "
                    "persistent permission failures."
                )
                confidence = Confidence.MEDIUM
            else:
                severity = Severity.CRITICAL if len(rbac_errors) >= 10 else Severity.WARNING
                transient_note = ""
                confidence = Confidence.HIGH

            sample = rbac_errors[:5]
            evidence_text = "\n".join(f"Line {num}: {text[:200]}" for num, text in sample)

            # Extract the specific resources that are failing
            failed_resources = set()
            resource_pattern = re.compile(r"Failed to (?:list|watch|get) \*(\S+)", re.IGNORECASE)
            for _, line_text in rbac_errors:
                match = resource_pattern.search(line_text)
                if match:
                    failed_resources.add(match.group(1))

            resource_list = ", ".join(sorted(failed_resources)[:10]) if failed_resources else "various resources"

            findings.append(_make_finding(
                title=f"RBAC permission errors in {component_name}",
                description=(
                    f"Detected {len(rbac_errors)} RBAC/permission error(s) in `{component_name}` logs "
                    f"affecting: {resource_list}.{transient_note}"
                ),
                severity=severity,
                namespace="kube-system",
                resource_name=lf.pod,
                resource_kind="Pod",
                evidence=[Evidence(
                    evidence_type=EvidenceType.LOG_LINE,
                    source_file=lf.path,
                    content=evidence_text,
                )],
                remediation=(
                    f"1. Verify ClusterRoleBinding exists: `kubectl get clusterrolebinding system:{component_name}`\n"
                    f"2. Check ClusterRole permissions: `kubectl describe clusterrole system:{component_name}`\n"
                    f"3. If errors are for specific resources (e.g., storageclasses, configmaps), check if the "
                    f"permissions exist in a separate ClusterRole (e.g., system:volume-scheduler)\n"
                    f"4. If transient (startup only), these may be race conditions and not require action"
                ),
                category="control-plane",
                confidence=confidence,
            ))

    return findings


def _check_log_errors(parsed: ParsedBundle) -> list[Finding]:
    findings = []
    for lf in parsed.log_files:
        if lf.size_bytes == 0:
            continue

        # Skip control plane components (handled by _check_control_plane_logs)
        is_control_plane = any(
            cp in lf.pod.lower() or cp in lf.container.lower()
            for cp in CONTROL_PLANE_COMPONENTS
        )
        if is_control_plane:
            continue

        errors = extract_error_lines(parsed.extraction_path, lf.path, context_lines=2)
        if len(errors) >= 5:
            sample = errors[:3]
            evidence_content = "\n---\n".join(
                f"Line {e['line_number']}: {e['match_line']}" for e in sample
            )

            findings.append(_make_finding(
                title=f"High error density in logs: {lf.pod}/{lf.container}",
                description=f"Found {len(errors)}+ error patterns in logs for container `{lf.container}` in pod `{lf.pod}` (namespace `{lf.namespace}`).{' (previous container)' if lf.is_previous else ''}",
                severity=Severity.WARNING,
                namespace=lf.namespace,
                resource_name=lf.pod,
                resource_kind="Pod",
                evidence=[Evidence(
                    evidence_type=EvidenceType.LOG_LINE,
                    source_file=lf.path,
                    content=evidence_content,
                )],
                remediation=f"Review full logs for `{lf.pod}/{lf.container}` to identify the root cause of errors.",
                category="logs",
                confidence=Confidence.MEDIUM,
            ))
    return findings


def build_timeline_events(parsed: ParsedBundle) -> list[TimelineEvent]:
    events = []
    for e in parsed.events:
        ts = e.last_timestamp or e.first_timestamp or ""
        # Include events even without timestamps — they still have diagnostic value
        if not ts:
            ts = "unknown"

        severity = Severity.INFO
        if e.event_type == "Warning":
            severity = Severity.WARNING
        if e.reason in ("NodeNotReady", "OOMKilling", "SystemOOM"):
            severity = Severity.CRITICAL

        events.append(TimelineEvent(
            timestamp=ts,
            event_type=e.reason,
            resource_kind=e.involved_object_kind,
            resource_name=e.involved_object_name,
            namespace=e.namespace,
            message=e.message,
            severity=severity,
        ))

    events.sort(key=lambda x: x.timestamp)
    return events


_HEALTH_DEDUCTIONS: dict[str, dict[str, int]] = {
    # Cluster-wide scope — these can take down everything
    "control-plane": {"critical": 20, "warning": 4, "info": 0},
    "node-health":   {"critical": 15, "warning": 5, "info": 0},
    # Workload scope — affects only that service
    "workload":      {"critical": 8,  "warning": 3, "info": 0},
    "pod-health":    {"critical": 6,  "warning": 2, "info": 0},
    "container-exit":{"critical": 4,  "warning": 2, "info": 0},
    "storage":       {"critical": 8,  "warning": 3, "info": 0},
    "scheduling":    {"critical": 6,  "warning": 2, "info": 0},
    # Low-signal categories
    "logs":          {"critical": 3,  "warning": 1, "info": 0},
    "events":        {"critical": 4,  "warning": 1, "info": 0},
    "probe-health":  {"critical": 4,  "warning": 2, "info": 0},
}
_DEFAULT_DEDUCTIONS = {"critical": 5, "warning": 2, "info": 0}


def calculate_health_score(findings: list[Finding]) -> int:
    score = 100
    for f in findings:
        sev_key = f.severity.value.lower()
        deductions = _HEALTH_DEDUCTIONS.get(f.category or "", _DEFAULT_DEDUCTIONS)
        score -= deductions.get(sev_key, 0)
    return max(0, min(100, score))
