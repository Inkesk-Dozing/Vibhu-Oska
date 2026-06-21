# Changelog

All notable changes to Vibhu-Oska are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning follows [Semantic Versioning](https://semver.org/).

---

## [Unreleased]

### Planned
- spaCy/stanza NER integration for higher-accuracy GRAG entity extraction
- Streaming token-by-token WebSocket output (currently full-response delivery)
- Multi-user session isolation with JWT-based auth flow
- Sovereign GPT fine-tuning pipeline from collected RLHF feedback events
- `Deep-Thought Mode` — internal MCTS reflection loop with multi-path scoring

---

## [0.2.0] — 2026-06-20

### Added

#### Infrastructure & Shared Contracts
- `pyproject.toml` with editable install (`pip install -e .`) and grouped dependencies
- `Shared/Models.py` — `TaskResponse`, `TokenUsage`, `PluginInfo`, `CoreStatus`, `ExecutionTarget` Pydantic v2 models
- Protocol Buffer schemas: `brain.proto`, `router.proto`, `common.proto`, `telemetry.proto`

#### Plugin System
- `Logger` — structlog-based structured logging with JSON (prod) and colored (dev) output
- `ConfigLoader` — YAML configuration with typed project-root resolution
- `BaseService` — abstract lifecycle contract for all injectable services
- `ToolRegistry` — dependency injection registry with `get_safe()` null-safe access
- `DatabaseConnector` — thread-safe async SQLite with migration runner and parameterized queries
- `CachePlugin` — in-memory LRU store with configurable TTL eviction
- Extended suite: `AuthenticationManager`, `Scheduler`, `SearchEngine`, `SelfUpdater`,
  `ThermalMonitor`, `ReplayLogger`, `FeedbackCollector`, `CodeAnalyzer`

#### Data & Memory Layer
- ChromaDB semantic memory store (`store_memory`, `query_memory` with cosine relevance scoring)
- SQLite knowledge graph — `kg_nodes` and `kg_edges` tables with FK cascade on delete
- Default eOzka entity seed: founders, subsidiaries, products, and organizational edges
- `query_knowledge_graph()` — 1-hop GRAG entity and edge traversal
- Cache warm-up on boot for recent sessions and user profiles

#### Intelligence Pipeline
- `ValidationCore` — SQL injection and XSS sanitization (input); JSON schema enforcement (output)
- `CognitionCore` — Norvig edit-distance spell checker; sovereign-gpt/direct-transformer routing
- `HybridCore` — hardware-aware CPU/GPU/NPU routing with health-gated failover
- `BackupCore` — deterministic keyword-matching fallback; zero external dependencies
- `MonitoringCore` — psutil-based CPU, RAM, GPU telemetry at configurable intervals
- `OptimizationCore` — relevance-ranked context pruning before prompt construction
- `OrchestratorCore` — double-validation lifecycle; RLHF event publishing; semantic response cache (0.92 threshold)

#### Event Bus & Gateway
- ZeroMQ PUB/SUB `EventBus` with typed `Topics` enum and `EventFactory`
- WebSocket `ConnectionManager` with broadcast and per-client routing
- FastAPI application with lifespan boot, 28 routes including:
  - `WS /ws/{session_id}` — streaming chat with GRAG context injection and message persistence
  - `POST /api/v1/memory/kg/ingest` — heuristic NER-based GRAG population
  - `POST /api/v1/corpus/append` — QA format detection and corpus append
  - `GET /api/v1/sessions` — recent session listing ordered by `updated_at`

#### Sovereign GPT
- `VibhuOskaGPT` — decoder-only transformer: RMSNorm, RoPE, SwiGLU FFN, weight-tied embedding/LM-head
- `SovereignBPETokenizer` — byte-pair encoding trained from scratch on local corpus
- Training pipeline with AdamW, OneCycleLR, gradient clipping, early stopping at ≥99.5% accuracy
- Self-contained Q&A corpus seed: Python, FastAPI, SQL, CSS, math, language, Vibhu-Oska Q&A
- `SovereignGPTGenerator` — temperature-controlled autoregressive sampling

#### Frontend Dashboard
- Dark-mode layout with glassmorphism panels and CSS custom property design system
- Chat panel: markdown + code block rendering, copy buttons, WebSocket exponential backoff reconnect
- Voice input (Web Speech API) and TTS output pipeline
- Camera feed: MediaPipe Hands gesture detection mapped to OS commands
- Memory panel: vector search, KG query, GRAG ingest form with live node/edge count
- Session history sidebar with `newSession()` flow and 30s auto-refresh
- Monitor panel: real-time Chart.js latency and event throughput graphs
- Training panel: live log stream, corpus append, Sovereign GPT controls
- Voice biometric lock: 3-sample pitch fingerprint gate (22% variance tolerance)
- RLHF feedback bar, execution replay log, task queue with live status indicators
- Auto-GRAG ingestion of AI responses after each generation

#### Infrastructure
- Multi-stage Dockerfile with CPU/GPU build targets (`DEVICE=cpu|gpu`)
- Docker Compose with health check, named volume for `Data/`, `.env` injection
- 65-test integration suite (happy path, boundary, adversarial inputs)
- `setup.sh`, `train_sovereign_gpt.sh`, `generate_protos.sh`

### Fixed
- `DataCore.query_memory()` keyword argument mismatch — Gateway was calling
  `query_memory(prompt=...)` instead of `query_memory(query_text=...)`,
  causing silent `TypeError` and empty context on every chat request.

### Changed
- Replaced monolithic stub files (`orchestrator.py`, `monitoring.py`, `optimization.py`,
  `backup1.py`, `data.py`, `HybridCore.py`, `functions.py`) with properly structured
  `StrictCamelCase` module directories, each containing an `__init__.py`.

---

## [0.1.0] — 2025-12-09

### Added
- Initial project scaffold: monorepo structure, basic branding, README
- Placeholder stubs for Backend, Frontend, Models, Shared directories
- `pyproject.toml` skeleton and basic `.gitignore`
