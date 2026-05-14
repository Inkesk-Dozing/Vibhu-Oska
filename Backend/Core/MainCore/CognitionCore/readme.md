# CognitionCore

The primary LLM reasoning interface. CognitionCore is the only module permitted to perform inference — nothing outside this file calls model weights directly.

## Responsibility

Accept a prompt + context, route to the best available local model, return a `TaskResponse`.

## Inference Hierarchy (Auto-Fallback Chain)

```
1. Sovereign GPT        (if Models/sovereign_gpt/checkpoints/sovereign_gpt.pt exists)
   ↓ fails
2. Qwen2.5-0.5B-Instruct (loads directly in-process via transformers)
   ↓ fails
3. Exception raised → HybridCore catches → BackupCore CPU rules
```

## Explicit Model Routing

Pass `model_id` to bypass auto-selection:

| model_id | Routes to |
|---|---|
| `sovereign-gpt` | Sovereign GPT custom checkpoint |
| `vibhu-core` | Qwen2.5-0.5B in-process direct |
| `direct-transformers` | Same as vibhu-core |
| `backup-1` | Handled by HybridCore → BackupCore |
| `""` (empty) | Auto-fallback chain (default) |

## Corpus Spell Checker

CognitionCore includes a Norvig-style spell checker trained on the local corpus (`Data/training/sovereign_gpt/corpus.txt`). If a typo is detected in the user prompt, the system prompt is modified to instruct the model to acknowledge and correct the typo before answering.

## Module Boundary Rules

- **No DB connections** — never touches ChromaDB or SQLite directly
- **No I/O scripts** — no file reads/writes except loading model weights on startup
- **No event bus calls** — inference is synchronous from the orchestrator's perspective

## Key File

`cognition.py` — 423 lines, 19.4KB

## Classes

| Class | Purpose |
|---|---|
| `CorpusSpellChecker` | Norvig probabilistic spell correction seeded with project corpus |
| `CognitionCore` | Main inference interface implementing `BaseService` |

## Methods

| Method | Description |
|---|---|
| `generate()` | Main entry point — auto-routes based on model_id |
| `generate_sovereign()` | Runs Sovereign GPT from local checkpoints |
| `generate_direct()` | Runs Qwen2.5 in-process via transformers |
| `load_direct_model()` | Lazy-loads transformer weights (first call only) |
