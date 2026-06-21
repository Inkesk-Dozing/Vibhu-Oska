# OptimizationCore

The query cache and context compression layer. OptimizationCore reduces redundant inference by serving cached responses for repeated prompts, and ensures context windows don't exceed model limits.

## Responsibility

- Intercept repeated prompts before they hit CognitionCore (LRU query cache)
- Compress and prune context chunks to stay within the configured token budget
- Save generated responses to the cache for future reuse

## How the Cache Works

1. OrchestratorCore calls `check_query_cache(prompt)` early in the pipeline
2. If a match exists in the LRU cache → response served immediately, CognitionCore is never called
3. After a successful inference → `save_response_cache(prompt, response)` persists the result
4. Cache key: normalized prompt string (lowercased, stripped)
5. Cache backend: in-memory LRU via CacheManager plugin (configurable size, default 256 entries)

## Context Compression

`optimize_prompt_context(context)` receives the combined context list (history + semantic + GRAG) and:
1. Scores each chunk by recency and relevance
2. Truncates to stay within `max_context_tokens` (configurable, default 1024)
3. Returns a pruned, ordered list of context dicts

## Module Boundary Rules

- **No inference** — never calls CognitionCore or any model
- **No raw DB access** — uses CacheManager plugin for in-memory store only

## Key File

`OptimizationCore.py`
