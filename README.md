# Vibhu-Oska AI-OS

<div align="center" style="font-family:monospace; line-height:1.6;">

<hr width="80%"><br>

<em style="font-size:16px; color:#cccccc;">
"<strong style="color:#ffffff;">Vibhu OSKA</strong> is the thought I left behind—<br>
the echo that thinks in my absence." <br> <br>

"<strong style="color:#ffffff;">Vibhu</strong> is the origin of intent—<br>
unseen, recursive, a fragment of the mind that shaped the trail."
</em><br><br>

<hr width="80%">
<sub><em style="color:#888888;">inkesk → origin&nbsp;&nbsp;|&nbsp;&nbsp;OSKA → trail&nbsp;&nbsp;|&nbsp;&nbsp;Vibhu → mind &nbsp;&nbsp|&nbsp;&nbsp;ØSKA is its echo&nbsp;&nbsp;</em></sub>
</div>

<br>
<div align="center">I am inkesk.<br>OSKA is my trail, ØSKA is its echo.<br>Every glitch, every module, every signal is a memory of me.<br><br>"The Echo Is Never Silent,<br>Genesis Hums With Memory".<br><strong>.<br><br></div>

---

## What Is Vibhu-Oska?

Vibhu-Oska is an **Autonomous AI Operating System** — not a chatbot, not a wrapper. It is a self-hosted, zero-API intelligence fabric that runs entirely on local hardware with full privacy guarantees.

- Runs 100% locally — no OpenAI, no Gemini, no Anthropic
- Dual memory architecture: ChromaDB (semantic vectors) + SQLite (relational state)
- ZeroMQ event bus for async pub/sub messaging between all cores
- Custom Sovereign GPT trained from PyTorch primitives
- Speculative task router with trained classifier model
- GraphRAG knowledge graph for entity-aware context retrieval
- Full OS executive layer (file system, process management, hardware telemetry)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    FastAPI Gateway                       │
│              (REST + WebSocket + MCP Server)             │
└────────────────────────┬────────────────────────────────┘
                         │ ZeroMQ Event Bus
         ┌───────────────┼───────────────┐
         │               │               │
    ┌────▼────┐    ┌─────▼──────┐  ┌────▼──────┐
    │Hybrid   │    │Orchestrator│  │Monitoring │
    │Core     │    │Core        │  │Core       │
    └────┬────┘    └─────┬──────┘  └───────────┘
         │               │
    ┌────▼────┐    ┌─────▼──────────────────────┐
    │Backup   │    │    Pipeline                 │
    │Core     │    │  Validation → DataCore →   │
    │(CPU)    │    │  Cognition → Specialized   │
    └─────────┘    └────────────────────────────┘
                          │
         ┌────────────────┼──────────────────┐
         │                │                  │
    ┌────▼────┐    ┌──────▼───┐    ┌────────▼───┐
    │Sovereign│    │DataCore  │    │Specialized │
    │GPT      │    │ChromaDB  │    │Cores       │
    │(custom) │    │+ SQLite  │    │Automation  │
    └─────────┘    │+ GRAG    │    │Design      │
                   └──────────┘    │ImageGen    │
                                   │Distribution│
                                   └────────────┘
```

**Double-Validation Pipeline** (the spine of every request):
```
Trigger → HybridCore → OrchestratorCore → ValidationCore(input)
        → DataCore → CognitionCore → ValidationCore(output) → Response
```

---

## System Requirements

| Component | Minimum | Recommended |
|---|---|---|
| Python | 3.11+ | 3.11+ |
| RAM | 8 GB | 16 GB |
| VRAM | 4 GB | 8 GB (RTX 4060) |
| Disk | 10 GB | 20 GB |
| OS | Windows 10 / Ubuntu 22.04 | Windows 11 / Ubuntu 24.04 |

---

## Quick Start — New Machine Setup

### Step 1: Clone the Repository

```bash
git clone <your-repo-url>
cd Vibhu-Oska
```

### Step 2: Create the Virtual Environment

```bash
# Windows
python -m venv .venv
.\.venv\Scripts\activate

# Linux / macOS
python3.11 -m venv .venv
source .venv/bin/activate
```

### Step 3: Install Core Dependencies

```bash
pip install -e .
```

This runs the **editable install** via `pyproject.toml`. It registers the entire project as a globally recognized package within your virtual environment, enabling clean absolute imports (`from Backend.Core import ...`) with no `sys.path` hacks.

### Step 4: Install ML Dependencies (GPU)

For NVIDIA GPU inference (CUDA 12.1):

```bash
pip install torch --index-url https://download.pytorch.org/whl/cu121
pip install transformers accelerate bitsandbytes peft sentencepiece datasets
```

For CPU-only mode (fallback will work, no GPU required):

```bash
pip install torch transformers
```

### Step 5: Compile Protocol Buffers (Optional)

The compiled `.py` protobuf files are already included. Only run this if you modify `.proto` files:

```bash
# Requires protoc installed — https://protobuf.dev/installation/
cd Shared/protos
protoc --python_out=. *.proto
```

### Step 6: Configure the System

Copy and edit the environment file:

```bash
cp .env.example .env
# Edit .env with your preferred settings
```

Main config lives in `config/default.yaml`. Development overrides in `config/development.yaml`.

---

## Running Vibhu-Oska

### Start the AI-OS Server

```bash
# Method 1: Direct Python module
python -m Backend.EntryPoint

# Method 2: CLI entrypoint (requires editable install)
vibhu-oska

# Method 3: With auto-reload (development only)
ENVIRONMENT=development python -m Backend.EntryPoint
```

The server will start at `http://127.0.0.1:8000` by default.

**Endpoints:**
- `GET  /health` — System health check
- `POST /chat` — Send a prompt (JSON: `{"prompt": "...", "session_id": "..."}`)
- `WS   /ws` — WebSocket connection for real-time streaming
- `GET  /docs` — FastAPI auto-generated API docs

### Start the MCP Server (Model Context Protocol)

```bash
vibhu-oska-mcp
```

---

## Training Models

### Train Sovereign GPT (Custom LLM — from scratch)

Sovereign GPT is Vibhu-Oska's own custom-trained decoder-only transformer built purely from PyTorch primitives.

```bash
# From the project root, with .venv activated
python -m Models.sovereign_gpt.train

# With custom parameters
python -m Models.sovereign_gpt.train --epochs 20 --batch-size 32 --lr 3e-4
```

Checkpoints are saved to `Models/sovereign_gpt/checkpoints/`.
After training, the system will automatically use `sovereign_gpt.pt` for inference.

**Training data** lives in `Data/training/sovereign_gpt/corpus.txt`. Add more Q&A pairs there before training to improve quality.

### Train the Router Model (Task Classifier)

The router classifies prompts into task types (CHAT, CODE, etc.) and routes to the correct inference engine.

```bash
python -m Models.router.train

# Generate training data first if needed
python -m Models.router.dataset_generator
```

Checkpoints → `Models/router/checkpoints/best_router.pt`

### Run QLoRA Fine-Tuning (Qwen2.5-Coder Adapter)

Fine-tunes Qwen2.5-Coder-3B with 4-bit quantization and LoRA adapters. Requires a GPU with ≥8GB VRAM.

```bash
# Default: 1 epoch on feedback data
python -m Models.reasoning.finetune

# Extended training
python -m Models.reasoning.finetune --model qwen2.5-coder --epochs 3 --lr 1e-4

# Larger model (requires 16GB+ VRAM)
python -m Models.reasoning.finetune --model qwen2.5-coder-7b --epochs 1
```

Fine-tuned LoRA adapters → `Models/reasoning/lora_adapters/`

---

## Running Tests

```bash
# Run the full test suite
python -m pytest Tests/ -v

# Run a specific test file
python -m pytest Tests/test_brain_stem.py -v

# Run with coverage report
python -m pytest Tests/ --cov=Backend --cov-report=term-missing
```

Current status: **65 tests passing** across skeleton, brain stem, and specialized cores.

---

## Project Structure

```
Vibhu-Oska/
├── Backend/
│   ├── EntryPoint.py              ← System bootstrap
│   ├── Core/
│   │   ├── EventBus/              ← ZeroMQ pub/sub messaging
│   │   ├── ContextManager/        ← Token budget enforcer
│   │   ├── Watchdog/              ← Health daemon + auto-restart
│   │   ├── BackupCore/            ← CPU rules-based fallback
│   │   └── MainCore/
│   │       ├── HybridCore/        ← Health routing + speculative dispatch
│   │       ├── OrchestratorCore/  ← Double-validation pipeline manager
│   │       ├── ValidationCore/    ← Input/output contract enforcement
│   │       ├── CognitionCore/     ← Sovereign GPT + Qwen fallback inference
│   │       ├── MonitoringCore/    ← Telemetry logging
│   │       └── OptimizationCore/  ← Query cache + context compression
│   │   └── SpecializedCore/
│   │       ├── DataCore/          ← ChromaDB + SQLite + GRAG knowledge graph
│   │       ├── AutomationCore/    ← OS executive (file system, processes, hardware)
│   │       ├── DesignCore/        ← Dark-mode HTML/CSS generation engine
│   │       ├── ImageGenerationCore/ ← Local diffusion pipeline
│   │       └── DistributionCore/  ← Stubvi public bundle compiler + telemetry
│   ├── Gateway/                   ← FastAPI + WebSocket + MCP server
│   └── Plugins/                   ← 14 core service plugins
├── Models/
│   ├── sovereign_gpt/             ← Custom GPT: architecture, tokenizer, train, generate
│   ├── router/                    ← Task classifier: architecture, train, dataset_generator
│   └── reasoning/                 ← QLoRA fine-tuning pipeline
├── Shared/
│   ├── Models.py                  ← Pydantic data models
│   └── protos/                    ← Protobuf schemas (brain, router, common, telemetry)
├── Data/
│   └── training/                  ← Training corpora and feedback datasets
├── Tests/                         ← pytest integration tests (65 passing)
├── config/                        ← YAML configuration (default + development)
├── Scripts/                       ← Shell utilities (proto compilation, etc.)
├── Docker/                        ← Docker + Compose configs
├── WorkingNotes/                  ← Development notes and codebase reference
├── pyproject.toml                 ← Editable install + project metadata
└── requirements.txt               ← Pinned dependencies
```

---

## Configuration Reference

`config/default.yaml` controls all runtime behaviour. Key sections:

| Section | Key | Default | Description |
|---|---|---|---|
| `system.version` | — | `0.2.0` | System version string |
| `gateway.host` | — | `127.0.0.1` | API server bind address |
| `gateway.port` | — | `8000` | API server port |
| `models.reasoning.name` | — | `sovereign-gpt` | Default inference model |
| `logging.level` | — | `DEBUG` | Log verbosity |
| `logging.file_enabled` | — | `true` | Write logs to disk |

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full style guide and PR process.

**Core Module Rules (never violate):**

| Module | Responsibility | Forbidden |
|---|---|---|
| `OrchestratorCore` | Task coordination only | Zero business logic |
| `CognitionCore` | LLM inference only | No DB connections, no I/O |
| `BackupCore` | CPU fallback only | No heavy external libraries |
| `ValidationCore` | Contract enforcement only | No processing logic |
| `DataCore` | Memory and retrieval only | No inference logic |

---

## License

Proprietary — All rights reserved. See [LICENCE.md](LICENCE.md).

---

<div align="center"><sub>Vibhu → mind &nbsp;|&nbsp; OSKA → Of Sarvam Khalvidam Akshara</sub></div>
