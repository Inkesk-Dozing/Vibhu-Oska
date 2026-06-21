# 07 — Plugins & Tool Registry

## The BaseService Contract

Every plugin implements this abstract interface:

```python
class BaseService(ABC):
    @abstractmethod
    def info(self) -> PluginInfo:
        """Return plugin metadata (name, version, capabilities, status)."""
        ...

    @abstractmethod
    def health_check(self) -> bool:
        """Return True if the plugin is operational."""
        ...

    @abstractmethod
    async def execute(self, action: str, **kwargs: Any) -> Any:
        """Main dispatch method. action is a string like 'query', 'generate', 'store'."""
        ...
```

This contract means every plugin is swappable — you could replace the in-memory LRU CacheManager with a Redis-backed one without touching any other code, as long as the new class implements BaseService.

## ToolRegistry

```
File: Backend/Plugins/ToolRegistry/Registry.py
```

The dependency injection container. Plugins are registered by name string and retrieved by name:

```python
# Registration (in Gateway lifespan)
registry.register("cognition", CognitionCore())
registry.register("data_core", DataCore())

# Retrieval (anywhere that has registry access)
cog = registry.get("cognition")          # raises KeyError if not found
cog = registry.get_safe("cognition")     # returns None if not found
```

## All 14 Plugins

### 1. Logger (`Logger/`)
```
structlog-based structured JSON logging.
Logger.get("ModuleName") → bound logger
Logger.initialize() → configure output level, format, file path
Logger.bind_request(id) / Logger.clear_context() → per-request tracing
```

### 2. ConfigLoader (`ConfigLoader/`)
```
YAML + .env config system.
ConfigLoader.load(project_root) → AppConfig object
config.get("system.version") → value with dot-path access
config.get_section("gateway") → dict of section
```

### 3. DatabaseConnector (`DatabaseConnector/`)
```
SQLite + aiosqlite async connection pool.
Runs schema migrations on startup (creates all 5 tables).
Seeds kg_nodes/kg_edges with Vibhu-Oska domain entities on first run.
Used by: DataCore, MonitoringCore, FeedbackCollector
```

### 4. CacheManager (`CacheManager/`)
```
In-memory LRU cache (configurable max_size, default 256).
Used by: OptimizationCore (query response cache)
```

### 5. ToolRegistry (`ToolRegistry/`)
```
Self-referential — the registry is itself a plugin.
Contains BaseService abstract + Registry container.
```

### 6. AuthenticationManager (`AuthenticationManager/`)
```
JWT token lifecycle management.
Actions: issue_token(user_id) → token, verify_token(token) → payload, refresh_token(token) → new_token
Secret from JWT_SECRET in .env
```

### 7. SearchEngine (`SearchEngine/`)
```
SearXNG wrapper for local federated web search.
Actions: query(q, num_results) → [{title, url, snippet}]
Requires: SearXNG Docker container running on localhost:8888
```

### 8. TestingFramework (`TestingFramework/`)
```
Sandboxed code execution + pytest runner.
Actions: run_code(code_str) → {stdout, stderr, exit_code}
         run_tests(test_dir) → {passed, failed, errors}
Used by: Stage 5 self-correction loop
```

### 9. CodeAnalyzer (`CodeAnalyzer/`)
```
Static analysis and AST parsing.
Actions: analyze(code) → {imports, functions, classes, complexity}
         lint(file_path) → {issues: [{line, message, severity}]}
```

### 10. FeedbackCollector (`FeedbackCollector/`)
```
RLHF signal collection.
Actions: record(prompt, response, reward, comment) → appends to Data/training/feedback/feedback_dataset.jsonl
Used by: Gateway /feedback endpoint, Stage 5 RLHF loop
```

### 11. ReplayLogger (`ReplayLogger/`)
```
Session action recording for training replay.
Records full action sequences (prompt → context → response → tool_calls) to JSONL.
Used by: Stage 5 autonomous training data generation
```

### 12. Scheduler (`Scheduler/`)
```
Cron-style background task scheduler.
Actions: add_job(func, cron_expr), remove_job(job_id), list_jobs()
Planned use: nightly Sovereign GPT retraining, weekly ChromaDB compaction
```

### 13. ThermalMonitor (`ThermalMonitor/`)
```
CPU/GPU temperature monitoring via psutil + torch.
Actions: get_temps() → {cpu_celsius, gpu_celsius}
         check_throttle() → bool (True if over threshold)
Publishes SYSTEM_ALERT if temperature exceeds configured limits.
```

### 14. SelfUpdater (`SelfUpdater/`)
```
Hot-append new code modules to SpecializedCore.
Actions: create_module(name, code, tests) → writes + validates new module
Used by: Stage 5 AGI recursive self-evolution loop
```
