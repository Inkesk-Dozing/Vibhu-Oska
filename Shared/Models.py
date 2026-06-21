"""
Vibhu-Oska AI-OS — Python Data Models
Pydantic equivalents of the Protobuf schemas for day-to-day Python usage.
These are the canonical Python types used throughout the Backend.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import IntEnum
from typing import Any

from pydantic import BaseModel, Field, ConfigDict


# ══════════════════════════════════════════════════════════════════════════════
# Common Types (mirrors common.proto)
# ══════════════════════════════════════════════════════════════════════════════


class StatusCode(IntEnum):
    UNKNOWN = 0
    OK = 1
    ERROR = 2
    PENDING = 3
    IN_PROGRESS = 4
    COMPLETED = 5
    FAILED = 6
    TIMEOUT = 7
    CANCELLED = 8


class ExecutionTarget(IntEnum):
    AUTO = 0
    CPU = 1
    GPU = 2
    NPU = 3


class Priority(IntEnum):
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


class Status(BaseModel):
    code: StatusCode = StatusCode.UNKNOWN
    message: str = ""
    details: str = ""


class RequestMetadata(BaseModel):
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = "system"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    priority: Priority = Priority.NORMAL
    target: ExecutionTarget = ExecutionTarget.AUTO
    labels: dict[str, str] = Field(default_factory=dict)


class ResponseMetadata(BaseModel):
    request_id: str = ""
    completed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    processing_time_ms: int = 0
    executed_on: ExecutionTarget = ExecutionTarget.CPU
    status: Status = Field(default_factory=Status)


# ══════════════════════════════════════════════════════════════════════════════
# Brain Types (mirrors brain.proto)
# ══════════════════════════════════════════════════════════════════════════════


class TaskType(IntEnum):
    UNKNOWN = 0
    CHAT = 1
    CODE_GENERATE = 2
    CODE_REVIEW = 3
    CODE_FIX = 4
    RESEARCH = 5
    ANALYZE = 6
    DESIGN = 7
    SYSTEM = 8
    MEMORY_STORE = 9
    MEMORY_RECALL = 10
    SELF_IMPROVE = 11
    SCHEDULE = 12


class ContextChunk(BaseModel):
    source: str = ""
    content: str = ""
    relevance_score: float = 0.0
    metadata: dict[str, str] = Field(default_factory=dict)


class ModelConfig(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    model_id: str = "vibhu-router-150m"
    temperature: float = 0.7
    max_tokens: int = 2048
    top_p: float = 0.9
    stop_sequences: list[str] = Field(default_factory=list)
    stream: bool = False
    target: ExecutionTarget = ExecutionTarget.AUTO


class TokenUsage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    context_window_remaining: int = 0


class ToolCall(BaseModel):
    tool_name: str = ""
    action: str = ""
    arguments_json: str = "{}"
    priority: Priority = Priority.NORMAL


class ToolResult(BaseModel):
    tool_name: str = ""
    action: str = ""
    status: Status = Field(default_factory=Status)
    result_json: str = "{}"
    execution_time_ms: int = 0


class Artifact(BaseModel):
    name: str = ""
    type: str = ""  # "code", "image", "document", "config"
    content: str = ""
    language: str = ""
    file_path: str = ""


class ThoughtStep(BaseModel):
    step_number: int = 0
    phase: str = ""  # "planning", "executing", "reflecting"
    thought: str = ""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CognitionTrace(BaseModel):
    steps: list[ThoughtStep] = Field(default_factory=list)
    total_reasoning_time_ms: int = 0


class TaskRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, protected_namespaces=())

    metadata: RequestMetadata = Field(default_factory=RequestMetadata)
    type: TaskType = TaskType.UNKNOWN
    prompt: str = ""
    context: list[ContextChunk] = Field(default_factory=list)
    model_config_field: ModelConfig = Field(default_factory=ModelConfig, alias="model_config")
    parameters: dict[str, str] = Field(default_factory=dict)


class TaskResponse(BaseModel):
    metadata: ResponseMetadata = Field(default_factory=ResponseMetadata)
    type: TaskType = TaskType.UNKNOWN
    content: str = ""
    artifacts: list[Artifact] = Field(default_factory=list)
    tool_calls: list[ToolCall] = Field(default_factory=list)
    trace: CognitionTrace = Field(default_factory=CognitionTrace)
    token_usage: TokenUsage = Field(default_factory=TokenUsage)


class MemoryQuery(BaseModel):
    metadata: RequestMetadata = Field(default_factory=RequestMetadata)
    query_text: str = ""
    collection: str = "default"
    top_k: int = 5
    min_relevance: float = 0.5


class MemoryStore(BaseModel):
    metadata: RequestMetadata = Field(default_factory=RequestMetadata)
    content: str = ""
    collection: str = "default"
    tags: dict[str, str] = Field(default_factory=dict)


class MemoryResult(BaseModel):
    metadata: ResponseMetadata = Field(default_factory=ResponseMetadata)
    chunks: list[ContextChunk] = Field(default_factory=list)
    total_results: int = 0


# ══════════════════════════════════════════════════════════════════════════════
# Router Types (mirrors router.proto)
# ══════════════════════════════════════════════════════════════════════════════


class EventType(IntEnum):
    UNKNOWN = 0
    USER_INPUT = 1
    SYSTEM_TELEMETRY = 2
    TASK_CREATED = 3
    TASK_COMPLETED = 4
    TASK_FAILED = 5
    TOOL_REQUEST = 6
    TOOL_RESULT = 7
    MODEL_LOADED = 8
    MEMORY_UPDATED = 9
    HEALTH_CHECK = 10
    ALERT = 11
    SCHEDULE_TRIGGER = 12
    SELF_REPAIR = 13


class EventEnvelope(BaseModel):
    """The universal message wrapper for the ZeroMQ event bus."""
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: EventType = EventType.UNKNOWN
    topic: str = ""
    source: str = ""
    destination: str = ""  # Empty = broadcast
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    priority: Priority = Priority.NORMAL
    payload: dict[str, Any] = Field(default_factory=dict)
    payload_type: str = ""


class RouteAction(IntEnum):
    UNKNOWN = 0
    TO_GPU = 1
    TO_NPU = 2
    TO_CPU = 3
    TO_PLUGIN = 4
    TO_CACHE = 5
    REJECT = 6
    QUEUE = 7


class RouteDecision(BaseModel):
    request_id: str = ""
    action: RouteAction = RouteAction.UNKNOWN
    target: ExecutionTarget = ExecutionTarget.AUTO
    plugin_name: str = ""
    confidence: float = 0.0
    reasoning: str = ""
    suggested_model: ModelConfig = Field(default_factory=ModelConfig)
    decided_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CoreStatus(IntEnum):
    UNKNOWN = 0
    HEALTHY = 1
    DEGRADED = 2
    OFFLINE = 3
    OVERLOADED = 4


class ResourceUsage(BaseModel):
    cpu_percent: float = 0.0
    ram_used_gb: float = 0.0
    ram_total_gb: float = 0.0
    gpu_vram_used_gb: float = 0.0
    gpu_vram_total_gb: float = 0.0
    gpu_temp_celsius: float = 0.0
    cpu_temp_celsius: float = 0.0
    disk_used_gb: float = 0.0
    disk_total_gb: float = 0.0


class SystemHealth(BaseModel):
    checked_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    internet_available: bool = False
    gpu_available: bool = False
    npu_available: bool = False
    orchestrator_status: CoreStatus = CoreStatus.UNKNOWN
    cognition_status: CoreStatus = CoreStatus.UNKNOWN
    data_status: CoreStatus = CoreStatus.UNKNOWN
    validation_status: CoreStatus = CoreStatus.UNKNOWN
    resources: ResourceUsage = Field(default_factory=ResourceUsage)
    active_mode: str = "main"  # "main", "backup", "cpu_only"


# ══════════════════════════════════════════════════════════════════════════════
# Telemetry Types (mirrors telemetry.proto)
# ══════════════════════════════════════════════════════════════════════════════


class Heartbeat(BaseModel):
    source: str = ""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    alive: bool = True
    uptime_seconds: int = 0
    pending_tasks: int = 0
    load_factor: float = 0.0


class MetricType(IntEnum):
    UNKNOWN = 0
    COUNTER = 1
    GAUGE = 2
    HISTOGRAM = 3
    TIMER = 4


class MetricPoint(BaseModel):
    name: str = ""
    type: MetricType = MetricType.GAUGE
    value: float = 0.0
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    labels: dict[str, str] = Field(default_factory=dict)


class AlertSeverity(IntEnum):
    INFO = 0
    WARNING = 1
    ERROR = 2
    CRITICAL = 3


class Alert(BaseModel):
    alert_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    severity: AlertSeverity = AlertSeverity.INFO
    source: str = ""
    title: str = ""
    description: str = ""
    fired_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    acknowledged: bool = False
    context: dict[str, str] = Field(default_factory=dict)


class ExecutionLog(BaseModel):
    request_id: str = ""
    phase: str = ""
    action: str = ""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    duration_ms: int = 0
    result: Status = Field(default_factory=Status)
    details: str = ""


# ══════════════════════════════════════════════════════════════════════════════
# Plugin Types
# ══════════════════════════════════════════════════════════════════════════════


class PluginInfo(BaseModel):
    name: str = ""
    version: str = "0.1.0"
    description: str = ""
    capabilities: list[str] = Field(default_factory=list)
    status: CoreStatus = CoreStatus.UNKNOWN
    registered_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    preferred_target: ExecutionTarget = ExecutionTarget.CPU
