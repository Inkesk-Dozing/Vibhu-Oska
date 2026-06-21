# BackupCore

The CPU-based rules fallback. BackupCore activates when every GPU inference path has failed. It provides deterministic, lightweight responses using pattern matching and rule-based logic — no external dependencies.

## Responsibility

Serve a response when Sovereign GPT and Qwen both fail. The response may be limited in quality, but the pipeline never crashes.

## Design Principles

- **No heavy libraries** — BackupCore must start instantly with zero GPU memory
- Uses regex and keyword pattern matching for basic intent classification
- Returns structured `TaskResponse` objects identical to CognitionCore's output
- Marks responses with `executed_on = ExecutionTarget.CPU` for traceability

## When It Activates

1. HybridCore's primary `generate()` call throws any exception
2. OrchestratorCore passes `model_id = "backup-1"` explicitly (forced backup mode)
3. Watchdog detects CognitionCore in DEGRADED state and flags for backup routing

## Module Boundary Rules

- **No external libraries** beyond stdlib — absolutely no transformers, torch, chromadb
- **No DB access** — BackupCore never touches SQLite or ChromaDB
- Must remain importable even if all ML packages are uninstalled

## Key File

`BackupCore.py` — 5.8KB
