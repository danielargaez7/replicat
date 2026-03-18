from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class AnalysisStatus(str, Enum):
    PENDING = "pending"
    EXTRACTING = "extracting"
    PARSING = "parsing"
    HEURISTIC_PASS = "heuristic_pass"
    AI_ANALYSIS = "ai_analysis"
    SYNTHESIS = "synthesis"
    COMPLETE = "complete"
    ERROR = "error"


class ContainerStatus(BaseModel):
    name: str
    ready: bool = False
    restart_count: int = 0
    state: str = "unknown"
    reason: Optional[str] = None
    exit_code: Optional[int] = None
    message: Optional[str] = None
    image: str = ""


class PodInfo(BaseModel):
    name: str
    namespace: str
    phase: str = "Unknown"
    status_reason: Optional[str] = None
    containers: list[ContainerStatus] = []
    conditions: list[dict] = []
    node_name: Optional[str] = None
    labels: dict[str, str] = {}
    creation_timestamp: Optional[str] = None


class NodeInfo(BaseModel):
    name: str
    ready: bool = True
    conditions: list[dict] = []
    capacity: dict[str, str] = {}
    allocatable: dict[str, str] = {}
    kernel_version: Optional[str] = None
    os_image: Optional[str] = None
    kubelet_version: Optional[str] = None


class EventInfo(BaseModel):
    namespace: str
    name: str = ""
    involved_object_kind: str = ""
    involved_object_name: str = ""
    reason: str = ""
    message: str = ""
    event_type: str = "Normal"
    first_timestamp: Optional[str] = None
    last_timestamp: Optional[str] = None
    count: int = 1
    source_component: Optional[str] = None


class DeploymentInfo(BaseModel):
    name: str
    namespace: str
    replicas: int = 0
    ready_replicas: int = 0
    available_replicas: int = 0
    unavailable_replicas: int = 0
    conditions: list[dict] = []


class ServiceInfo(BaseModel):
    name: str
    namespace: str
    service_type: str = "ClusterIP"
    cluster_ip: Optional[str] = None
    ports: list[dict] = []
    selector: dict[str, str] = {}


class LogFile(BaseModel):
    namespace: str
    pod: str
    container: str
    path: str
    size_bytes: int = 0
    is_previous: bool = False


class ParsedBundle(BaseModel):
    bundle_id: str
    extraction_path: str
    cluster_version: Optional[dict] = None
    namespaces: list[str] = []
    nodes: list[NodeInfo] = []
    pods: list[PodInfo] = []
    deployments: list[DeploymentInfo] = []
    services: list[ServiceInfo] = []
    events: list[EventInfo] = []
    log_files: list[LogFile] = []
    raw_file_tree: list[str] = []
    errors: list[str] = Field(default_factory=list, description="Parse errors encountered")


class BundleMetadata(BaseModel):
    id: str
    filename: str
    upload_time: datetime
    status: AnalysisStatus = AnalysisStatus.PENDING
    file_count: int = 0
    size_bytes: int = 0
