# 02 — Event Bus (ZeroMQ Pub/Sub)

## What It Is

The nervous system of Vibhu-Oska. Every core communicates exclusively through the EventBus — no direct method calls between cores at the system level. This creates total decoupling: any core can be added, removed, or swapped without touching any other core.

## Files

```
Backend/Core/EventBus/
├── EventBus.py    ← Broker implementation (10.9KB)
├── Events.py      ← Event dataclass + EventFactory (6.1KB)
└── Topics.py      ← All topic name constants (2.9KB)
```

## The Event Dataclass

```python
@dataclass
class Event:
    event_id:  str    # UUID4 — unique per event
    topic:     str    # Routing key (e.g., "user.input")
    source:    str    # Who published it (e.g., "gateway", "orchestrator")
    payload:   dict   # Arbitrary JSON-serializable data
    timestamp: float  # Unix timestamp (time.time())
```

Events are serialized to JSON for transport over ZeroMQ sockets.

## EventFactory Convenience Methods

```python
# Create a standardized task_created event
event = EventFactory.task_created(task_id="abc123", task_type="chat", prompt="Hello")

# Create an alert event
event = EventFactory.alert(source="validation", title="Input rejected", description="...", severity=1)

# Create a tool request
event = EventFactory.tool_request(tool_name="search", action="query", arguments={"q": "..."})
```

## Topic Constants (`Topics.py`)

```python
Topics.USER_INPUT        = "user.input"
Topics.TASK_CREATED      = "task.created"
Topics.TASK_COMPLETED    = "task.completed"
Topics.TASK_FAILED       = "task.failed"
Topics.SYSTEM_ALERT      = "system.alert"
Topics.TOOL_REQUEST      = "tool.request"
Topics.HEALTH_CHECK      = "system.health"
Topics.MONITORING_LOG    = "monitoring.log"

# Dynamic topic per tool
Topics.tool_result_for("search") → "tool.result.search"
```

## How Pub/Sub Works

```python
# Subscribe (in OrchestratorCore.start())
await event_bus.subscribe(Topics.USER_INPUT, self.handle_user_input)

# Publish (in Gateway when a chat request arrives)
event = Event(topic=Topics.USER_INPUT, source="gateway", payload={"prompt": "...", "session_id": "..."})
await event_bus.publish(event)

# The bus calls handle_user_input(event) on the next async tick
```

## ZeroMQ Internals

EventBus uses an in-process PUSH/PULL socket pair to bridge the FastAPI async event loop with the subscriber callbacks:
- Publisher sends serialized Event bytes over PUSH socket
- Background task reads from PULL socket, deserializes, dispatches to subscribers
- Subscribers are `async def` callables — awaited in the event loop

This pattern means the Gateway's `POST /chat` handler returns immediately after publishing the USER_INPUT event — it does not block waiting for inference. The WebSocket connection is how the response is returned to the client.

## Subscriber Registration Lifecycle

```
Gateway lifespan startup
  → EventBus.start()                    # Start ZMQ sockets + dispatch loop
  → OrchestratorCore.start(event_bus)   # Subscribe to USER_INPUT
  → MonitoringCore.initialize(event_bus) # Subscribe to TASK_*, ALERT
  → Watchdog.start(event_bus)           # Subscribe to HEALTH_CHECK
```

All subscriptions are registered during lifespan startup. No subscriptions are created at module import time.
