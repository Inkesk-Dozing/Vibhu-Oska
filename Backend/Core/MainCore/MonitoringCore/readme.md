# MonitoringCore

The telemetry sink. MonitoringCore subscribes to the ZeroMQ EventBus and logs every meaningful system event to the SQLite telemetry database for persistent observability.

## Responsibility

Listen for events on the bus, extract structured telemetry, write to the `telemetry_events` SQLite table. Zero business logic — pure observation and recording.

## Events Monitored

| Event Topic | What Gets Logged |
|---|---|
| `TASK_CREATED` | task_id, task_type, timestamp |
| `TASK_COMPLETED` | task_id, processing_time_ms, token_usage |
| `TASK_FAILED` | task_id, error_message, timestamp |
| `SYSTEM_ALERT` | severity, title, description |
| `HEALTH_CHECK` | core_name, status, response_time_ms |

## Module Boundary Rules

- **No inference** — MonitoringCore never touches CognitionCore or model weights
- **No business logic** — does not modify events, only reads and persists them
- Writes only to the `telemetry_events` table via DatabaseConnector plugin

## Key File

`MonitoringCore.py` — 6.2KB

## Initialization

```python
await monitoring.initialize(registry, event_bus)
# Subscribes to TASK_CREATED, TASK_COMPLETED, TASK_FAILED, ALERT topics automatically
```
