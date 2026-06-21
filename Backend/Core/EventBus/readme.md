# EventBus

The ZeroMQ-based asynchronous pub/sub messaging backbone. Every core in Vibhu-Oska communicates exclusively through the EventBus — no direct method calls between cores at the system level.

## Files

| File | Purpose |
|---|---|
| `EventBus.py` | Core pub/sub broker (10.9KB) |
| `Events.py` | `Event` dataclass + `EventFactory` helpers (6.1KB) |
| `Topics.py` | All topic name constants (2.9KB) |

## How It Works

EventBus uses ZeroMQ PUSH/PULL sockets internally with an in-process async loop:

1. Publishers call `await event_bus.publish(event)` — fire and forget
2. The bus routes the event to all subscribers registered for that topic
3. Subscribers are async callables: `async def handler(event: Event) -> None`

## Event Structure

```python
@dataclass
class Event:
    event_id: str           # UUID — unique per event
    topic: str              # Routing key (see Topics.py)
    source: str             # Module that published the event
    payload: dict           # Arbitrary JSON-serializable data
    timestamp: float        # Unix timestamp (time.time())
```

## EventFactory Helpers

```python
EventFactory.task_created(task_id, task_type, prompt)
EventFactory.alert(source, title, description, severity)
EventFactory.tool_request(tool_name, action, arguments)
```

## Key Topics

```python
Topics.USER_INPUT          # "user.input"       — new user prompt
Topics.TASK_CREATED        # "task.created"     — session established
Topics.TASK_COMPLETED      # "task.completed"   — response ready
Topics.TASK_FAILED         # "task.failed"      — pipeline error
Topics.SYSTEM_ALERT        # "system.alert"     — health/validation alerts
Topics.TOOL_REQUEST        # "tool.request"     — plugin execution request
Topics.HEALTH_CHECK        # "system.health"    — watchdog ping
```

## Why ZeroMQ?

ZeroMQ enables true async decoupling. OrchestratorCore doesn't know about MonitoringCore; MonitoringCore doesn't know about ValidationCore. Any module can listen to any topic without tight coupling. This makes the system extensible (new cores subscribe to existing topics without modifying existing code) and testable (mock the bus, inject events directly).
