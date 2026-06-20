# 01 — Entry Point & Boot Sequence

## File: `Backend/EntryPoint.py`

The master bootstrap. When you run `python -m Backend.EntryPoint` or `vibhu-oska`, this file is the first thing Python executes.

## Boot Sequence (Step by Step)

```python
def main() -> None:
    # 1. Windows event loop fix
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    # 2. Load configuration
    config = ConfigLoader.load(project_root=project_root)

    # 3. Initialize logging
    Logger.initialize(level, fmt, output_dir, ...)

    # 4. Print banner with version/codename/tier
    log.info("Vibhu-Oska AI-OS | Version: 0.2.0 | Environment: development")

    # 5. Launch uvicorn → FastAPI Gateway
    uvicorn.run("Backend.Gateway.App:app", host="127.0.0.1", port=8000, reload=True)
```

The EntryPoint itself is intentionally minimal. The real initialization happens inside FastAPI's **lifespan manager** in `Gateway/App.py`.

## Gateway Lifespan (What Actually Starts the System)

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # STARTUP ──────────────────────────────────────────────
    # 1. Initialize EventBus (ZeroMQ PUSH/PULL sockets)
    # 2. Create ToolRegistry
    # 3. Initialize all 14 plugins (Logger, DB, Cache, Auth, ...)
    # 4. Initialize OrchestratorCore (subscribes to USER_INPUT topic)
    # 5. Start Watchdog daemon (background health polling)
    # 6. System is LIVE — accepting requests

    yield  # ← Application runs here

    # SHUTDOWN ─────────────────────────────────────────────
    # 1. OrchestratorCore.shutdown() → DataCore.shutdown()
    # 2. EventBus teardown
    # 3. DB connection pools closed
```

## ConfigLoader (`Backend/Plugins/ConfigLoader/`)

Loads configuration in this priority order:
1. `config/default.yaml` — base configuration
2. `config/{ENVIRONMENT}.yaml` — environment overlay (development.yaml)
3. `.env` file — environment variable overrides
4. System environment variables — highest priority

Access config values:
```python
config.get("system.version")          # → "0.2.0"
config.get_section("gateway")         # → {"host": "127.0.0.1", "port": 8000}
config.get("gateway.port", 9000)     # → 8000 (with default)
```

## Logger (`Backend/Plugins/Logger/`)

structlog-based structured JSON logging. Every module gets its own logger:
```python
log = Logger.get("MyModule")
log.info("Event", key="value", count=42)
# Output: {"event": "Event", "key": "value", "count": 42, "logger": "MyModule", "timestamp": "..."}
```

Request IDs are bound per-request:
```python
Logger.bind_request(request_id)   # All subsequent logs in this thread carry the request_id
Logger.clear_context()            # Clean up after request completes
```

Log files written to `Log/vibhu_oska.jsonl` (configurable).

## CLI Entry Points (`pyproject.toml`)

```toml
[project.scripts]
vibhu-oska = "Backend.EntryPoint:main"
vibhu-oska-mcp = "Backend.Gateway.McpServer:main"
```

These are registered when you run `pip install -e .`. After that, `vibhu-oska` works from any terminal with the venv activated.
