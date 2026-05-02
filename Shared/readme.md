# Shared — Cross-Package Models and Protocols

The `Shared` package contains data contracts used by every layer of the system. It has no business logic and no dependencies on Backend or Frontend — it is the common type vocabulary.

## Files

| File | Purpose |
|---|---|
| `Models.py` | Pydantic v2 data models — all request/response types (11.5KB) |
| `protos/` | Protobuf `.proto` schemas + compiled `_pb2.py` files |

## Key Models (`Models.py`)

### Core Response Types

```python
class TaskResponse(BaseModel):
    content: str                    # The AI-generated response text
    tool_calls: list[ToolCall]      # Any tool calls the model requested
    token_usage: TokenUsage         # prompt_tokens, completion_tokens, total_tokens
    metadata: ResponseMetadata      # status, processing_time_ms, executed_on

class TokenUsage(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int

class ResponseMetadata(BaseModel):
    status: Status
    processing_time_ms: int
    executed_on: ExecutionTarget    # GPU | CPU | NPU
```

### Status Types

```python
class StatusCode(IntEnum):
    PENDING = 1
    PROCESSING = 2
    COMPLETED = 5
    FAILED = 6

class Status(BaseModel):
    code: StatusCode
    message: str

class CoreStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILED = "failed"
    UNKNOWN = "unknown"
```

### Routing Types

```python
class ExecutionTarget(str, Enum):
    GPU = "gpu"
    CPU = "cpu"
    NPU = "npu"    # Planned: AMD Lemonade ONNX runtime

class PluginInfo(BaseModel):
    name: str
    version: str
    description: str
    capabilities: list[str]
    status: CoreStatus
    preferred_target: ExecutionTarget
```

## Protobuf Schemas (`protos/`)

| Schema | Purpose |
|---|---|
| `brain.proto` | Core task request/response wire format |
| `router.proto` | Router prediction message format |
| `common.proto` | Shared enum definitions |
| `telemetry.proto` | Telemetry event wire format |

Protobuf is used for high-performance binary serialization in the EventBus and for the MCP server. Pydantic models are used for the REST API and internal Python-to-Python data passing.

## Import Rule

Always import from `Shared.Models` — never from `Backend.*` within the Shared package:

```python
from Shared.Models import TaskResponse, StatusCode, CoreStatus
```
