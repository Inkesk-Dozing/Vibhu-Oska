# OrchestratorCore

The tactical request lifecycle manager. Sits at the center of the double-validation pipeline, coordinating every core without containing any business logic of its own.

## Responsibility

OrchestratorCore receives user input events from the ZeroMQ EventBus and drives the 8-step processing pipeline to completion. It never thinks — it delegates.

## The 8-Step Pipeline

```
1. ValidationCore      → Input guard (fail fast on malformed or dangerous prompts)
2. OptimizationCore    → Cache check (serve instantly if seen before)
3. DataCore            → Create session + persist interaction
4. DataCore            → Context retrieval (history + semantic + GraphRAG)
5. OptimizationCore    → Context pruning (stay within token budget)
6. SpecializedCore     → Pre-cognition dispatch (image/design/OS if matched)
7. HybridCore          → Default cognition path (Sovereign GPT → Qwen → BackupCore)
8. ValidationCore      → Output guard (schema validation before publishing)
```

## Specialized Core Pre-routing

Before reaching HybridCore, the orchestrator runs a keyword classifier:

| Trigger keywords | Routed to |
|---|---|
| `generate image`, `draw`, `paint`, `render image` | ImageGenerationCore |
| `design`, `layout`, `html`, `interface`, `webpage` | DesignCore |
| `list files`, `run command`, `cpu usage`, `system info` | AutomationCore |

If none match → falls through to HybridCore (default LLM path).

## Module Boundary Rules

- **Zero business logic** — OrchestratorCore never makes decisions about content
- No direct model calls — always delegates to HybridCore or SpecializedCores
- No direct DB queries — always delegates to DataCore

## Key File

`OrchestratorCore.py` — 474 lines, 23.4KB

## Event Topics Consumed

- `Topics.USER_INPUT` — triggers the full pipeline

## Event Topics Published

- `Topics.TASK_CREATED` — after session is established
- `Topics.TASK_COMPLETED` — on successful response
- `Topics.TASK_FAILED` — on validation failure or exception
- `Topics.ALERT` — on input validation rejection
- `Topics.TOOL_REQUEST` / `Topics.tool_result_for(name)` — for tool calls
