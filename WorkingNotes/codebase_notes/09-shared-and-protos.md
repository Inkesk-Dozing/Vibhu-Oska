# 09 — Shared Package: Models & Protocols

## Overview

`Shared/` is the common type vocabulary. It has zero business logic and zero dependencies on Backend or Frontend. Every layer imports from here — never the other way around.

```
Shared/
├── Models.py       ← All Pydantic v2 data models (11.5KB)
└── protos/
    ├── brain.proto       ← Core request/response wire format
    ├── router.proto      ← Router prediction message
    ├── common.proto      ← Shared enum types
    └── telemetry.proto   ← Telemetry event wire format
```

---

## Models.py — Complete Type Reference

### Response Chain

```python
class TaskResponse(BaseModel):
    content: str                    # AI-generated text
    tool_calls: list[ToolCall] = [] # Requested tool executions
    token_usage: TokenUsage
    metadata: ResponseMetadata

class ToolCall(BaseModel):
    tool_name: str       # Matches a registered plugin name
    action: str          # Action to dispatch
    arguments_json: str  # JSON-encoded kwargs

class TokenUsage(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int

class ResponseMetadata(BaseModel):
    status: Status
    processing_time_ms: int = 0
    executed_on: ExecutionTarget = ExecutionTarget.CPU
    model_id: str = ""
```

### Status System

```python
class StatusCode(IntEnum):
    PENDING    = 1
    PROCESSING = 2
    PAUSED     = 3
    CANCELLED  = 4
    COMPLETED  = 5
    FAILED     = 6

class Status(BaseModel):
    code: StatusCode
    message: str

class CoreStatus(str, Enum):
    HEALTHY  = "healthy"
    DEGRADED = "degraded"
    FAILED   = "failed"
    UNKNOWN  = "unknown"
```

### Routing Types

```python
class ExecutionTarget(str, Enum):
    GPU = "gpu"
    CPU = "cpu"
    NPU = "npu"     # Planned: AMD Lemonade ONNX runtime

class PluginInfo(BaseModel):
    name: str
    version: str
    description: str
    capabilities: list[str]
    status: CoreStatus
    preferred_target: ExecutionTarget
```

### Request Types (Gateway inbound)

```python
class ChatRequest(BaseModel):
    prompt: str
    session_id: str
    user_id: str = "operator"
    model_id: str = ""              # Empty = auto-route
    temperature: float = 0.7
    max_tokens: int = 512

class HealthResponse(BaseModel):
    status: str                     # "healthy" | "degraded"
    version: str
    cores: dict[str, str]           # {core_name: CoreStatus}
    uptime_seconds: float
```

---

## Protobuf Schemas

Protobuf is used for:
- High-performance binary serialization in the EventBus (large payloads)
- MCP server wire format
- Future NPU deployment (ONNX models use protobuf-adjacent formats)

### brain.proto

```protobuf
message BrainRequest {
  string request_id = 1;
  string prompt = 2;
  string session_id = 3;
  string model_id = 4;
  repeated ContextChunk context = 5;
}

message BrainResponse {
  string content = 1;
  int32 status_code = 2;
  int32 prompt_tokens = 3;
  int32 completion_tokens = 4;
  int32 processing_time_ms = 5;
}
```

### router.proto

```protobuf
message RouterRequest {
  string request_id = 1;
  string prompt = 2;
}

message RouterPrediction {
  string task_type = 1;       // CHAT | CODE | OS | DESIGN | IMAGE
  string target_model = 2;    // sovereign-gpt | vibhu-core | backup
  float task_confidence = 3;
  float target_confidence = 4;
}
```

### telemetry.proto

```protobuf
message TelemetryEvent {
  string event_id = 1;
  string topic = 2;
  string source = 3;
  string payload_json = 4;
  double timestamp = 5;
}
```

---

## Import Rule

```python
# ✅ Correct — always import from Shared.Models
from Shared.Models import TaskResponse, StatusCode, CoreStatus

# ❌ Wrong — Shared must never import from Backend
from Backend.Core.MainCore.OrchestratorCore import ...  # never in Shared/
```
