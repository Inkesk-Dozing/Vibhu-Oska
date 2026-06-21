# Gateway

The FastAPI application layer — the external surface of Vibhu-Oska. All client communication passes through here: REST API requests, WebSocket connections, and MCP tool calls.

## Files

| File | Purpose |
|---|---|
| `App.py` | Main FastAPI app with lifespan manager, all REST endpoints, WebSocket handler (26KB) |
| `McpServer.py` | Model Context Protocol server (MCP) for tool integration (8.8KB) |

## Endpoints

### REST API

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | System health — queries Watchdog registry |
| `GET` | `/status` | Extended status (version, cores, uptime) |
| `POST` | `/chat` | Submit a prompt (fires USER_INPUT event) |
| `GET` | `/sessions/{session_id}` | Retrieve session history |
| `GET` | `/models` | List available inference models |
| `POST` | `/admin/train` | Trigger Sovereign GPT training |
| `POST` | `/admin/flush-cache` | Clear OptimizationCore LRU cache |

### WebSocket

```
WS /ws
```

Real-time bidirectional channel. The eOzka/SentientHub.tsx frontend connects here. Messages flow:

- **Inbound**: `{"prompt": "...", "session_id": "..."}` JSON
- **Outbound**: `{"content": "...", "status": "completed", "processing_time_ms": 123}` JSON

The WebSocket handler subscribes to `Topics.TASK_COMPLETED` / `Topics.TASK_FAILED` on the EventBus and forwards results back to the connected client.

## App Lifespan

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # STARTUP: EventBus, ToolRegistry, all Plugins, OrchestratorCore, Watchdog
    yield
    # SHUTDOWN: Graceful teardown of all cores
```

## MCP Server

`McpServer.py` implements the Model Context Protocol for IDE / tooling integration. Exposes Vibhu-Oska's capabilities as MCP tools callable by compatible clients.

Start: `vibhu-oska-mcp`

## CORS Configuration

Development: all origins allowed.
Production: configure `ALLOWED_ORIGINS` in `.env`.

## Key File

`App.py` — 26KB
