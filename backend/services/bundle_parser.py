"""
Extracts and parses Troubleshoot support bundles into structured data.

Handles the standard bundle directory structure:
  cluster-info/, cluster-resources/, pods/logs/, events/, etc.
"""

from __future__ import annotations

import json
import os
import tarfile
from pathlib import Path
from typing import Any, Optional

from models.bundle import (
    ContainerStatus,
    DeploymentInfo,
    EventInfo,
    LogFile,
    NodeInfo,
    ParsedBundle,
    PodInfo,
    ServiceInfo,
)


async def parse_bundle(bundle_id: str, bundle_path: str) -> ParsedBundle:
    extract_dir = os.path.join("uploads", bundle_id, "extracted")
    os.makedirs(extract_dir, exist_ok=True)

    # Use streaming extraction (pipe mode 'r|gz') — processes members as
    # they're read from the compressed stream instead of seeking through
    # the entire archive first. Saves 10-30s on large bundles.
    with tarfile.open(bundle_path, "r|gz") as tar:
        tar.extractall(extract_dir, filter="data")

    root = _find_bundle_root(extract_dir)
    file_tree = _build_file_tree(root)

    parsed = ParsedBundle(
        bundle_id=bundle_id,
        extraction_path=root,
        raw_file_tree=file_tree,
    )

    parsed.cluster_version = _parse_cluster_version(root, parsed)
    parsed.namespaces = _parse_namespaces(root, parsed)
    parsed.nodes = _parse_nodes(root, parsed)
    parsed.pods = _parse_pods(root, parsed)
    parsed.deployments = _parse_deployments(root, parsed)
    parsed.services = _parse_services(root, parsed)
    parsed.events = _parse_events(root, parsed)
    parsed.log_files = _index_log_files(root)

    return parsed


def _find_bundle_root(extract_dir: str) -> str:
    """Find the actual root directory inside the extracted bundle."""
    entries = os.listdir(extract_dir)
    if len(entries) == 1 and os.path.isdir(os.path.join(extract_dir, entries[0])):
        return os.path.join(extract_dir, entries[0])
    return extract_dir


def _build_file_tree(root: str) -> list[str]:
    tree = []
    for dirpath, _, filenames in os.walk(root):
        for f in filenames:
            rel = os.path.relpath(os.path.join(dirpath, f), root)
            tree.append(rel)
    return sorted(tree)


def _safe_load_json(path: str, errors: list[str]) -> Any | None:
    try:
        with open(path) as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError, PermissionError) as e:
        errors.append(f"Failed to parse {path}: {e}")
        return None


def _parse_cluster_version(root: str, parsed: ParsedBundle) -> dict | None:
    path = os.path.join(root, "cluster-info", "cluster_version.json")
    return _safe_load_json(path, parsed.errors)


def _parse_namespaces(root: str, parsed: ParsedBundle) -> list[str]:
    path = os.path.join(root, "cluster-resources", "namespaces.json")
    data = _safe_load_json(path, parsed.errors)
    if not data or not isinstance(data, list):
        return []
    return [ns.get("metadata", {}).get("name", "") for ns in data if ns.get("metadata", {}).get("name")]


def _parse_nodes(root: str, parsed: ParsedBundle) -> list[NodeInfo]:
    path = os.path.join(root, "cluster-resources", "nodes.json")
    data = _safe_load_json(path, parsed.errors)
    if not data or not isinstance(data, list):
        return []

    nodes = []
    for item in data:
        meta = item.get("metadata", {})
        status = item.get("status", {})
        conditions = status.get("conditions", [])
        ready = any(
            c.get("type") == "Ready" and c.get("status") == "True"
            for c in conditions
        )
        node_info = status.get("nodeInfo", {})

        nodes.append(NodeInfo(
            name=meta.get("name", "unknown"),
            ready=ready,
            conditions=conditions,
            capacity=status.get("capacity", {}),
            allocatable=status.get("allocatable", {}),
            kernel_version=node_info.get("kernelVersion"),
            os_image=node_info.get("osImage"),
            kubelet_version=node_info.get("kubeletVersion"),
        ))
    return nodes


def _parse_pods(root: str, parsed: ParsedBundle) -> list[PodInfo]:
    pods_dir = os.path.join(root, "cluster-resources", "pods")
    if not os.path.isdir(pods_dir):
        return []

    pods = []
    for ns_name in os.listdir(pods_dir):
        ns_path = os.path.join(pods_dir, ns_name)
        if not os.path.isdir(ns_path) or ns_name == "logs":
            continue

        for pod_file in os.listdir(ns_path):
            if not pod_file.endswith(".json"):
                continue
            data = _safe_load_json(os.path.join(ns_path, pod_file), parsed.errors)
            if not data:
                continue

            pod = _parse_single_pod(data, ns_name)
            if pod:
                pods.append(pod)
    return pods


def _parse_single_pod(data: dict, namespace: str) -> PodInfo | None:
    meta = data.get("metadata", {})
    status = data.get("status", {})
    spec = data.get("spec", {})

    containers = []
    for cs in status.get("containerStatuses", []) + status.get("initContainerStatuses", []):
        state_info = cs.get("state", {})
        state_key = next(iter(state_info), "unknown")
        state_detail = state_info.get(state_key, {})

        containers.append(ContainerStatus(
            name=cs.get("name", ""),
            ready=cs.get("ready", False),
            restart_count=cs.get("restartCount", 0),
            state=state_key,
            reason=state_detail.get("reason"),
            exit_code=state_detail.get("exitCode"),
            message=state_detail.get("message"),
            image=cs.get("image", ""),
        ))

    phase = status.get("phase", "Unknown")
    status_reason = status.get("reason")

    # Check container statuses for waiting reasons (CrashLoopBackOff, etc.)
    if not status_reason:
        for cs in status.get("containerStatuses", []):
            waiting = cs.get("state", {}).get("waiting", {})
            if waiting.get("reason"):
                status_reason = waiting["reason"]
                break

    return PodInfo(
        name=meta.get("name", "unknown"),
        namespace=namespace,
        phase=phase,
        status_reason=status_reason,
        containers=containers,
        conditions=status.get("conditions", []),
        node_name=spec.get("nodeName"),
        labels=meta.get("labels", {}),
        creation_timestamp=meta.get("creationTimestamp"),
    )


def _parse_deployments(root: str, parsed: ParsedBundle) -> list[DeploymentInfo]:
    deploy_dir = os.path.join(root, "cluster-resources", "deployments")
    if not os.path.isdir(deploy_dir):
        return []

    deployments = []
    for ns_name in os.listdir(deploy_dir):
        ns_path = os.path.join(deploy_dir, ns_name)
        if not os.path.isdir(ns_path):
            continue

        for dep_file in os.listdir(ns_path):
            if not dep_file.endswith(".json"):
                continue
            data = _safe_load_json(os.path.join(ns_path, dep_file), parsed.errors)
            if not data:
                continue

            meta = data.get("metadata", {})
            status = data.get("status", {})
            spec = data.get("spec", {})

            deployments.append(DeploymentInfo(
                name=meta.get("name", "unknown"),
                namespace=ns_name,
                replicas=spec.get("replicas", 0),
                ready_replicas=status.get("readyReplicas", 0),
                available_replicas=status.get("availableReplicas", 0),
                unavailable_replicas=status.get("unavailableReplicas", 0),
                conditions=status.get("conditions", []),
            ))
    return deployments


def _parse_services(root: str, parsed: ParsedBundle) -> list[ServiceInfo]:
    svc_dir = os.path.join(root, "cluster-resources", "services")
    if not os.path.isdir(svc_dir):
        return []

    services = []
    for ns_name in os.listdir(svc_dir):
        ns_path = os.path.join(svc_dir, ns_name)
        if not os.path.isdir(ns_path):
            continue

        for svc_file in os.listdir(ns_path):
            if not svc_file.endswith(".json"):
                continue
            data = _safe_load_json(os.path.join(ns_path, svc_file), parsed.errors)
            if not data:
                continue

            meta = data.get("metadata", {})
            spec = data.get("spec", {})

            services.append(ServiceInfo(
                name=meta.get("name", "unknown"),
                namespace=ns_name,
                service_type=spec.get("type", "ClusterIP"),
                cluster_ip=spec.get("clusterIP"),
                ports=spec.get("ports", []),
                selector=spec.get("selector", {}),
            ))
    return services


def _parse_events(root: str, parsed: ParsedBundle) -> list[EventInfo]:
    # Try multiple known event directory locations
    events_dir = None
    for candidate in [
        os.path.join(root, "cluster-resources", "events"),
        os.path.join(root, "events"),
        os.path.join(root, "cluster-resources", "events.k8s.io"),
    ]:
        if os.path.isdir(candidate):
            events_dir = candidate
            break

    if not events_dir:
        return []

    events = []
    for event_file in os.listdir(events_dir):
        if not event_file.endswith(".json"):
            continue
        ns_name = event_file.replace(".json", "")
        data = _safe_load_json(os.path.join(events_dir, event_file), parsed.errors)
        if not data or not isinstance(data, list):
            continue

        for item in data:
            meta = item.get("metadata", {})
            involved = item.get("involvedObject", {})

            # Handle both legacy (firstTimestamp/lastTimestamp) and
            # modern (eventTime/metadata.creationTimestamp) K8s event formats.
            # K8s 1.25+ often has null legacy timestamps.
            first_ts = (
                item.get("firstTimestamp")
                or item.get("eventTime")
                or meta.get("creationTimestamp")
            )
            last_ts = (
                item.get("lastTimestamp")
                or item.get("eventTime")
                or meta.get("creationTimestamp")
            )

            # Also handle series events (events.k8s.io/v1)
            series = item.get("series")
            if series and isinstance(series, dict):
                last_ts = series.get("lastObservedTime") or last_ts

            events.append(EventInfo(
                namespace=ns_name,
                name=meta.get("name", ""),
                involved_object_kind=involved.get("kind", ""),
                involved_object_name=involved.get("name", ""),
                reason=item.get("reason", ""),
                message=item.get("message") or item.get("note", ""),
                event_type=item.get("type", "Normal"),
                first_timestamp=first_ts,
                last_timestamp=last_ts,
                count=item.get("count") or (series.get("count", 1) if series else 1),
                source_component=(
                    item.get("source", {}).get("component")
                    or item.get("reportingComponent", "")
                ),
            ))
    return events


def _index_log_files(root: str) -> list[LogFile]:
    logs_dir = os.path.join(root, "cluster-resources", "pods", "logs")
    if not os.path.isdir(logs_dir):
        return []

    log_files = []
    for ns_name in os.listdir(logs_dir):
        ns_path = os.path.join(logs_dir, ns_name)
        if not os.path.isdir(ns_path):
            continue

        for pod_name in os.listdir(ns_path):
            pod_path = os.path.join(ns_path, pod_name)
            if not os.path.isdir(pod_path):
                continue

            for log_name in os.listdir(pod_path):
                log_path = os.path.join(pod_path, log_name)
                if not os.path.isfile(log_path):
                    continue

                is_previous = "-previous" in log_name
                container = log_name.replace("-previous.log", "").replace(".log", "")

                log_files.append(LogFile(
                    namespace=ns_name,
                    pod=pod_name,
                    container=container,
                    path=os.path.relpath(log_path, root),
                    size_bytes=os.path.getsize(log_path),
                    is_previous=is_previous,
                ))
    return log_files


def read_log_file(root: str, rel_path: str, max_lines: int = 500) -> str:
    full_path = os.path.join(root, rel_path)
    if not os.path.isfile(full_path):
        return ""
    try:
        with open(full_path, errors="replace") as f:
            lines = f.readlines()
        if len(lines) <= max_lines:
            return "".join(lines)
        head = lines[:max_lines // 4]
        tail = lines[-(max_lines * 3 // 4):]
        return "".join(head) + f"\n... [{len(lines) - max_lines} lines truncated] ...\n" + "".join(tail)
    except Exception:
        return ""


def extract_error_lines(root: str, rel_path: str, context_lines: int = 3) -> list[dict]:
    """Extract lines containing error indicators with surrounding context."""
    import re
    error_pattern = re.compile(
        r"(error|fatal|panic|exception|oom|killed|timeout|refused|failed|crash|segfault|SIGKILL|SIGSEGV)",
        re.IGNORECASE,
    )

    full_path = os.path.join(root, rel_path)
    if not os.path.isfile(full_path):
        return []

    try:
        with open(full_path, errors="replace") as f:
            lines = f.readlines()
    except Exception:
        return []

    matches = []
    seen_ranges: set[int] = set()

    for i, line in enumerate(lines):
        if error_pattern.search(line) and i not in seen_ranges:
            start = max(0, i - context_lines)
            end = min(len(lines), i + context_lines + 1)
            excerpt = "".join(lines[start:end])
            matches.append({
                "line_number": i + 1,
                "content": excerpt.strip(),
                "match_line": line.strip(),
            })
            seen_ranges.update(range(start, end))

            if len(matches) >= 20:
                break

    return matches
