# Backend — Package Overview

The `Backend` package is the entire server-side intelligence layer of Vibhu-Oska.
Every request that enters the system — from a REST call, a WebSocket message,
or an MCP tool invocation — is processed here before a response is returned.

## Package Map

```
Backend/
├── EntryPoint.py          ← System bootstrap (config → logging → uvicorn)
├── Core/                  ← All cognitive and operational cores
│   ├── EventBus/          ← ZeroMQ async pub/sub messaging backbone
│   ├── ContextManager/    ← Token budget and context window management
│   ├── Watchdog/          ← Service health daemon with auto-restart
│   ├── BackupCore/        ← CPU-based rules fallback when GPU cores fail
│   └── MainCore/          ← The primary intelligence pipeline
│       ├── HybridCore/        ← Health routing + speculative dispatch
│       ├── OrchestratorCore/  ← Double-validation request lifecycle manager
│       ├── ValidationCore/    ← Input sanitization + output schema enforcement
│       ├── CognitionCore/     ← Sovereign GPT + Qwen2.5 inference interface
│       ├── MonitoringCore/    ← EventBus subscriber + SQLite telemetry sink
│       └── OptimizationCore/  ← LRU query cache + context compression
│   └── SpecializedCore/   ← Domain-specific execution engines
│       ├── DataCore/          ← ChromaDB + SQLite + GraphRAG knowledge graph
│       ├── AutomationCore/    ← OS executive: files, processes, hardware
│       ├── DesignCore/        ← HTML/CSS layout generation engine
│       ├── ImageGenerationCore/ ← Local latent diffusion pipeline
│       └── DistributionCore/  ← Stubvi compiler + telemetry ingestion
├── Gateway/               ← FastAPI app + WebSocket server + MCP interface
└── Plugins/               ← 14 injectable service plugins (Logger, DB, Cache, etc.)
```

## Import Convention

All imports within the Backend package use **absolute paths only**:

```python
from Backend.Core.MainCore.CognitionCore.cognition import CognitionCore
from Backend.Plugins.Logger.Logger import Logger
from Shared.Models import TaskResponse
```

No `sys.path.append`, no `../../Core` relative paths — ever.

## Entry Point

`python -m Backend.EntryPoint` or the `vibhu-oska` CLI command boots the system:

1. Loads `config/default.yaml` via ConfigLoader
2. Initializes structured logging via Logger plugin
3. Launches the FastAPI Gateway with uvicorn
4. The Gateway's lifespan handler starts the EventBus, registers all plugins, and starts the OrchestratorCore subscriber
