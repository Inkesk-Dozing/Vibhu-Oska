# Watchdog

The service health daemon. Watchdog runs as a background async loop, periodically polling all registered cores for health status and triggering auto-restart when a degraded state is detected.

## Responsibility

- Poll registered `BaseService` implementations via `health_check()` on a configurable interval
- Detect DEGRADED / FAILED states and attempt controlled restarts
- Publish `SYSTEM_ALERT` events to the EventBus when health changes
- Maintain a live health registry accessible by the Gateway's `/health` endpoint

## Health States

| CoreStatus | Meaning | Watchdog Action |
|---|---|---|
| `HEALTHY` | Normal operation | No action |
| `DEGRADED` | Partial failure | Log warning + alert event |
| `FAILED` | Core unresponsive | Attempt restart; if 3 consecutive failures → alert severity HIGH |
| `UNKNOWN` | Not yet initialized | Log warning; retry on next cycle |

## Configuration

```yaml
watchdog:
  poll_interval_seconds: 30
  max_restart_attempts: 3
```

## Key File

`Watchdog.py` — 6.3KB

## Integration with Gateway

The Gateway's `/health` endpoint queries Watchdog's live registry directly, returning a structured JSON report of all core statuses. This is the authoritative system health surface.
