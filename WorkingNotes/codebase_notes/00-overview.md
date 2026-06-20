# 00 — Vibhu-Oska: Project Overview

## What This Is

Vibhu-Oska is an **Autonomous AI Operating System** — a self-hosted, zero-API intelligence fabric. It is not a chatbot, not a framework wrapper, and not a cloud-dependent application. Every byte of inference, every model weight, every database record lives on your local machine.

The system operates as a persistent background layer — always listening, routing, and responding through a combination of:
- Custom transformer models (trained from scratch in PyTorch)
- A dual memory system (semantic vectors + relational state)
- A ZeroMQ event bus connecting all cores asynchronously
- An OS executive layer for file system, process, and hardware interaction

## Philosophy

> *"Vibhu is the origin of intent — unseen, recursive, a fragment of the mind that shaped the trail."*

- **Vibhu** (विभु): Mind, all-pervading, the eternal
- **OSKA**: Of Sarvam Khalvidam Akshara — "All this is indeed the imperishable"
- The system is engineered as an extension of the creator's cognitive intent, not a product.

## Hard Constraints (Never Violate)

1. **Zero cloud APIs** — No OpenAI, Gemini, Anthropic, or any third-party inference endpoint
2. **No Ollama / vLLM / LM Studio** — no local background binary services
3. **All weights native** — model weights, tokenizers, and logic exist as project assets
4. **PyTorch primitives only** for model construction (no high-level frameworks like Keras)
5. **Absolute imports only** — no sys.path.append, no ../../Core relative paths

## Stage Map (Build Progression)

```
Stage 1: The Skeleton      ✅ COMPLETE
  → Protobuf schemas, ZeroMQ EventBus, Logger, ConfigLoader, FastAPI Gateway, editable install

Stage 2: The Brain Stem    ✅ COMPLETE
  → DataCore (ChromaDB + SQLite + GRAG), OrchestratorCore, ValidationCore,
    CognitionCore, HybridCore, all 14 plugins, MonitoringCore, OptimizationCore,
    ContextManager, Watchdog, AuthenticationManager, 8→65 tests passing

Stage 3: The Cortex        ✅ COMPLETE
  → Sovereign GPT (trained, 5.2MB), Router model (trained, 3MB, 10 epochs),
    QLoRA fine-tuning pipeline, AutomationCore (OS executive),
    DesignCore (HTML/CSS generation), ImageGenerationCore (diffusion pipeline),
    DistributionCore (Stubvi compiler + telemetry)

Stage 4: The Eyes & Hands  🔲 NEXT
  → Web Dashboard (Next.js/Vite full UI), SearXNG Docker, Unity 3D prototype

Stage 5: The Conscience    🔲 FUTURE
  → Self-correction loop, RLHF-Lite, ReplayLogger activation, Autonomous Scheduler

Stage 6: The Armor         🔲 FUTURE
  → JWT enforcement, Docker sandbox, rate limiting, production hardening

Stage 7: The Offering      🔲 FUTURE
  → Model distillation, Stubvi public API, differential privacy, landing page
```

## Repository Root

```
C:\Users\USER\Desktop\Extras\.i-oska\Vibhu-Oska\
```

## Technology Stack

| Layer | Technology |
|---|---|
| Language | Python 3.11+ |
| Web Framework | FastAPI + uvicorn |
| Event Bus | ZeroMQ (pyzmq) |
| Vector Memory | ChromaDB |
| Relational Memory | SQLite + aiosqlite |
| Cache | In-memory LRU (CacheManager plugin) |
| ML Training | PyTorch (custom from scratch) |
| GPU Inference | Sovereign GPT / Qwen2.5-0.5B |
| Serialization | Protobuf + Pydantic v2 |
| Logging | structlog + rich |
| Testing | pytest + pytest-asyncio (65 tests) |
| Containerization | Docker + Docker Compose |
| Frontend | Next.js (eOzka project — separate repo) |
