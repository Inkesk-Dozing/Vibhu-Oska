# HybridCore

The execution target router. HybridCore sits between OrchestratorCore and CognitionCore, managing health state and directing requests to the primary GPU inference engine or the CPU backup core.

## Responsibility

- Assess whether the primary LLM engine (Sovereign GPT / Qwen) is online
- Run speculative routing: classify the prompt via the trained Router model, assign the best model_id
- Fall back to BackupCore on any primary failure without crashing the pipeline

## Speculative Routing

HybridCore lazy-loads the trained Router model (`Models/router/checkpoints/best_router.pt`) on first request. The router classifies each prompt into a task type:

| Task Prediction | model_id Assigned | Routes to |
|---|---|---|
| `CODE` | `vibhu-core` | Qwen2.5-0.5B-Instruct in-process |
| `CHAT` | `sovereign-gpt` | Custom Sovereign GPT checkpoint |
| Unknown / error | `sovereign-gpt` | Default fallback |

If router checkpoints don't exist, speculative routing is disabled and `sovereign-gpt` is used as default.

## Fallback Chain

```
Primary (GPU) → fails → BackupCore (CPU rules-based)
```

The response `metadata.executed_on` field records which target served the request (`GPU` or `CPU`).

## Key File

`HybridCore.py` — 185 lines, 8.1KB

## Module Boundary Rules

- **No business logic** — only routing decisions
- Never accesses DataCore or ValidationCore directly
- Health check uses a lightweight `generate("ping", max_tokens=1)` probe
