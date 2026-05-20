# ContextManager

Token budget enforcer for the double-validation pipeline. Ensures that the combined context (chat history + semantic memory + GRAG knowledge graph) fed into CognitionCore never exceeds the model's effective context window.

## Responsibility

- Receive a list of context chunks from OrchestratorCore
- Count tokens for each chunk using a lightweight tokenization estimate
- Prune low-priority chunks until the total fits within `max_context_tokens`
- Return the trimmed context list

## Prioritization Strategy

Chunks are prioritized in this order before pruning:

1. **GraphRAG / knowledge graph** entries (highest — structured entity facts)
2. **Semantic memory** entries (medium — vector-retrieved relevant context)
3. **Chat history** entries (lowest priority — oldest messages pruned first)

## Configuration

`config/default.yaml`:
```yaml
context_manager:
  max_context_tokens: 1024
  token_estimate_method: word_count  # or tiktoken if installed
```

## Key File

`ContextManager.py` — 6KB

## Why This Matters

Sovereign GPT (default config) has `max_seq_len = 256`. Without context pruning, a long conversation history would silently overflow the model's input capacity, producing garbage output. ContextManager prevents this at the system level.
