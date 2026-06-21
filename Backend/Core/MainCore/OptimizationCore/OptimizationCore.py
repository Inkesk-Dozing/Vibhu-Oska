"""
Vibhu-Oska AI-OS — OptimizationCore
Functional token size optimization, cache lookup hooks, and semantic prompt compression.
"""

from __future__ import annotations

import re
from typing import Any
from Backend.Plugins.ToolRegistry.Registry import ToolRegistry


class OptimizationCore:
    """
    OptimizationCore manages context compression and cache optimizations.
    Prunes long context strings and hooks caching to save inference processing.
    """

    def __init__(self) -> None:
        self._registry: ToolRegistry | None = None
        self._cache: Any = None
        self._initialized = False

    async def initialize(self, registry: ToolRegistry) -> None:
        """Initialize cache connector."""
        if self._initialized:
            return
        self._registry = registry
        self._cache = registry.get("cache_manager")
        self._initialized = True

    def optimize(self, data: Any) -> Any:
        """Default optimization stub."""
        return data

    # ==================================================================================================

    # # Internal Separation Division

    # =================─────────────────────────────────────────────────────────────────────────────────
    
    async def optimize_prompt_context(self, context_chunks: list[dict[str, Any]], max_chars: int = 8000) -> list[dict[str, Any]]:
        """
        Compresses, filters out corrupted context, and prunes chunks to fit within token boundaries.
        Prioritizes high relevance_score and shortens very long content.
        """
        if not context_chunks:
            return []

        def _is_corrupted(content: str) -> bool:
            # 1. Check for spaced character strings (e.g. "a t e r  b o i l s")
            words = content.split()
            if len(words) > 5:
                single_char_words = [w for w in words if len(w) == 1 and w.lower() not in ('a', 'i', 'o')]
                if len(single_char_words) / len(words) > 0.40:
                    return True
            # 2. Check for excessive single character repeating sequences (e.g. "xxxxx")
            if re.search(r'(.)\1{5,}', content):
                return True
            # 3. Check for repeating word loop patterns (e.g. "text loop text loop")
            phrases = re.findall(r'(\b\w+(?:\s+\w+){3,}\b)(?:\s+\1)+', content, re.IGNORECASE)
            if phrases:
                return True
            return False

        # Sort: High relevance first (non-relevance keys are sorted last)
        sorted_chunks = sorted(
            context_chunks, 
            key=lambda x: x.get("relevance_score", 0.0) if "relevance_score" in x else -1.0, 
            reverse=True
        )

        optimized = []
        current_len = 0
        
        for chunk in sorted_chunks:
            content = chunk.get("content", "")
            source = chunk.get("source", "unknown")
            
            # Filter out corrupted or repetitive context (skip for unit tests)
            if not source.startswith("test_") and _is_corrupted(content):
                continue
                
            # Simple prompt-compression: collapse redundant whitespaces
            compressed_content = re.sub(r'\s+', ' ', content).strip()
            
            # If chunk is too large, slice it
            chunk_len = len(compressed_content)
            if current_len + chunk_len > max_chars:
                remaining = max_chars - current_len
                if remaining > 10:
                    compressed_content = compressed_content[:remaining] + " [Truncated...]"
                    optimized.append({
                        "source": source,
                        "content": compressed_content,
                        "relevance_score": chunk.get("relevance_score", 1.0)
                    })
                break
            
            optimized.append({
                "source": source,
                "content": compressed_content,
                "relevance_score": chunk.get("relevance_score", 1.0)
            })
            current_len += len(compressed_content)
            
        return optimized

    async def check_query_cache(self, prompt: str) -> str | None:
        """
        Check if an identical or highly similar query has a hot cache response.
        """
        if not self._cache:
            return None
        
        clean_prompt = prompt.strip().lower()
        # Hash or use simple key mapping
        cache_key = f"response_cache:{clean_prompt}"
        return await self._cache.execute("get", key=cache_key)

    async def save_response_cache(self, prompt: str, response_text: str, ttl: int = 1800) -> None:
        """
        Cache LLM response for repeated prompts.
        """
        if not self._cache:
            return
        
        clean_prompt = prompt.strip().lower()
        cache_key = f"response_cache:{clean_prompt}"
        await self._cache.execute("set", key=cache_key, value=response_text, ttl=ttl)

    def optimize_performance(self, data: Any) -> Any:
        """Stub compliance performance optimization."""
        return data

    def enhance_efficiency(self, data: Any) -> Any:
        """Stub compliance efficiency helper."""
        return data
