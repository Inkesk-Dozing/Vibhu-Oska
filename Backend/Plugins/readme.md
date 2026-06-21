# Plugins

The 14 injectable service plugins that power Vibhu-Oska's infrastructure layer. All plugins implement the `BaseService` abstract interface and are registered in the `ToolRegistry` at startup.

## BaseService Contract

```python
class BaseService(ABC):
    @abstractmethod
    def info(self) -> PluginInfo: ...          # Plugin metadata
    @abstractmethod
    def health_check(self) -> bool: ...        # Liveness probe
    @abstractmethod
    async def execute(self, action: str, **kwargs) -> Any: ...  # Main dispatch
```

## ToolRegistry

The ToolRegistry is the dependency injection container. All plugins register here during Gateway lifespan startup:

```python
registry.register("logger", Logger())
registry.register("cognition", CognitionCore())
registry.register("data_core", DataCore())
# ... all 14 plugins
```

Cores access plugins via `registry.get("plugin_name")` or `registry.get_safe("plugin_name")` (non-throwing).

## Plugin Directory

| Plugin | Folder | Purpose |
|---|---|---|
| Logger | `Logger/` | structlog-based structured JSON logging |
| ConfigLoader | `ConfigLoader/` | YAML + env var config system |
| DatabaseConnector | `DatabaseConnector/` | SQLite + aiosqlite, schema migrations, KG tables |
| CacheManager | `CacheManager/` | In-memory LRU cache (configurable size) |
| ToolRegistry | `ToolRegistry/` | Plugin container + BaseService abstract |
| AuthenticationManager | `AuthenticationManager/` | JWT token issue, verify, refresh |
| SearchEngine | `SearchEngine/` | SearXNG wrapper for local web search |
| TestingFramework | `TestingFramework/` | Sandboxed code execution + test runner |
| CodeAnalyzer | `CodeAnalyzer/` | Static analysis, AST parsing |
| FeedbackCollector | `FeedbackCollector/` | RLHF signal collection → feedback_dataset.jsonl |
| ReplayLogger | `ReplayLogger/` | Session action recording for training replay |
| Scheduler | `Scheduler/` | Cron-style task scheduler (nightly retrain, etc.) |
| ThermalMonitor | `ThermalMonitor/` | CPU/GPU temperature monitoring + throttle alerts |
| SelfUpdater | `SelfUpdater/` | Hot-append new code modules to SpecializedCore |

## Logger Plugin

The foundational plugin. All cores call `Logger.get("ModuleName")` to receive a structlog logger bound to that context. Outputs JSON logs to `Log/` directory (configurable).

```python
from Backend.Plugins.Logger.Logger import Logger
log = Logger.get("MyModule")
log.info("Event occurred", key="value")
```

## DatabaseConnector Plugin

Manages all SQLite access via aiosqlite. Runs schema migrations on startup. Tables:

| Table | Content |
|---|---|
| `sessions` | Session metadata (id, user_id, created_at) |
| `chat_messages` | Conversation turns (session_id, role, content, timestamp) |
| `telemetry_events` | System event log (MonitoringCore writes here) |
| `kg_nodes` | Knowledge graph entity nodes (GRAG) |
| `kg_edges` | Knowledge graph entity relationships (GRAG) |

## AuthenticationManager Plugin

Issues and validates JWT tokens. The Gateway's protected endpoints require a valid `Authorization: Bearer <token>` header. Tokens are signed with the `JWT_SECRET` from `.env`.
