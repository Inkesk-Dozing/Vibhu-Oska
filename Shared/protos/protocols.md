# Vibhu-Oska AI-OS — Protocol Definitions

## Overview

All inter-core communication in the Vibhu-Oska AI-OS is strictly typed using Protocol Buffers.
This ensures that the Backend (Python), Web Frontend (TypeScript), and Unity Frontend (C#) all
speak the same data language.

## Schema Files

| File | Package | Purpose |
|------|---------|---------|
| `common.proto` | `vibhu_oska.common` | Shared types: Timestamp, UUID, Status, ExecutionTarget, Priority, Metadata |
| `brain.proto` | `vibhu_oska.brain` | Cognitive payloads: TaskRequest, TaskResponse, Memory, ToolCall, Artifacts |
| `router.proto` | `vibhu_oska.router` | Event routing: EventEnvelope, RouteDecision, SystemHealth, PluginRegistry |
| `telemetry.proto` | `vibhu_oska.telemetry` | Observability: Heartbeat, Metrics, Alerts, ExecutionLog, ReplayRecord |

## Compilation

Generate language-specific bindings:

```bash
# Python
protoc --python_out=Shared/generated/ Shared/protos/*.proto

# C# (Unity)
protoc --csharp_out=Frontend/unity_app/Assets/Plugins/Protobuf/ Shared/protos/*.proto

# TypeScript (Web)
protoc --ts_out=Frontend/web_app/src/generated/ Shared/protos/*.proto
```

## Python Usage

For day-to-day Python development, use the Pydantic models in `Shared/models.py` instead of
raw Protobuf objects. They mirror the proto schemas exactly but provide Pythonic access patterns,
type safety, and JSON serialization.

```python
from Shared.models import TaskRequest, TaskType, Priority

request = TaskRequest(
    type=TaskType.CODE_GENERATE,
    prompt="Write a sorting algorithm",
)
```

## Rules

1. **Never hardcode message structures** — always reference proto-defined types
2. **Update all 3 bindings** when changing a proto file
3. **Use RequestMetadata/ResponseMetadata** on every message for traceability
4. **Prefer Pydantic models** in Python code, Protobufs for cross-language contracts
