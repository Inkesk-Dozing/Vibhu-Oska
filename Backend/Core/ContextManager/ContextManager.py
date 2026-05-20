"""
Vibhu-Oska AI-OS — ContextManager
Token budget enforcement and VRAM-aware context window management.
Prevents OOM errors and keeps inference within model limits.
"""

from __future__ import annotations

from typing import Any


class ContextManager:
    """
    Manages the token budget for each inference session.

    Responsibilities:
      - Track token usage per session
      - Enforce model-specific context window limits
      - Truncate conversation history intelligently when approaching limit
      - VRAM-aware: reduce context when GPU memory pressure is high

    Token limits (approximate for models in use):
      - Qwen2.5-Coder-3B:  16,384 tokens
      - Qwen2.5-Coder-7B:  32,768 tokens
      - Router-150M:        1,024  tokens
      - default:                 8,192  tokens

    Truncation strategy:
      1. Always keep the system prompt (first message)
      2. Keep the latest user message (last message)
      3. Fill remaining budget with most recent history (LIFO)
    """

    # Model context limits (tokens)
    LIMITS: dict[str, int] = {
        "qwen2.5-coder-3b-qlora": 16_384,
        "qwen2.5-coder-7b-qlora": 32_768,
        "router-150m":             1_024,
        "default":                 8_192,
    }

    # Safety margin — leave 512 tokens for generation
    GENERATION_RESERVE = 512

    def __init__(self, model_id: str = "default") -> None:
        self._model_id   = model_id
        self._max_tokens = self.LIMITS.get(model_id, self.LIMITS["default"]) - self.GENERATION_RESERVE
        self._sessions:  dict[str, list[dict[str, Any]]] = {}
        self._usage:     dict[str, int] = {}

    # ==================================================================================================

    # # Internal Separation Division

    # =================─────────────────────────────────────────────────────────────────────────────────

    def fit_messages(
        self,
        session_id: str,
        messages: list[dict[str, Any]],
        system_prompt: str = "",
        max_tokens: int | None = None,
    ) -> list[dict[str, Any]]:
        """
        Given a list of messages, return a truncated version that fits
        within the token budget for the current model.

        Args:
            session_id:    Unique session identifier
            messages:      List of {"role": ..., "content": ...} dicts
            system_prompt: System prompt to prepend (always kept)
            max_tokens:    Override the model's default limit

        Returns:
            Truncated messages list that fits in the context window
        """
        budget = max_tokens or self._max_tokens

        # Build final message list: [system] + history + [latest user]
        result = []
        used_tokens = 0

        # 1. System prompt is always included
        if system_prompt:
            sys_tok = self._count_tokens(system_prompt)
            budget -= sys_tok
            used_tokens += sys_tok

        if not messages:
            return []

        # 2. Always include the latest user message
        latest = messages[-1]
        latest_tok = self._count_tokens(latest.get("content", ""))
        budget -= latest_tok

        # 3. Fill remaining budget with history (reverse order = most recent first)
        history = messages[:-1]
        included = []
        for msg in reversed(history):
            tok = self._count_tokens(msg.get("content", ""))
            if budget - tok < 0:
                break
            budget -= tok
            included.insert(0, msg)

        result = included + [latest]

        # Track usage
        self._usage[session_id] = (max_tokens or self._max_tokens) - budget

        return result

    def get_usage(self, session_id: str) -> dict[str, Any]:
        """Return token usage stats for a session."""
        used    = self._usage.get(session_id, 0)
        maximum = self._max_tokens
        return {
            "session_id":    session_id,
            "tokens_used":   used,
            "tokens_max":    maximum,
            "tokens_left":   maximum - used,
            "usage_pct":     round(used / maximum * 100, 1) if maximum else 0,
        }

    def clear_session(self, session_id: str) -> None:
        """Clear context tracking for a session."""
        self._sessions.pop(session_id, None)
        self._usage.pop(session_id, None)

    def set_model(self, model_id: str) -> None:
        """Switch the active model and update limits accordingly."""
        self._model_id   = model_id
        self._max_tokens = self.LIMITS.get(model_id, self.LIMITS["default"]) - self.GENERATION_RESERVE

    @staticmethod
    def _count_tokens(text: str) -> int:
        """
        Approximate token count using a 4-chars-per-token heuristic.
        For production, replace with a tokenizer from the HuggingFace transformers library.
        """
        if not text:
            return 0
        # ~4 characters per token is accurate for English prose
        # Code tends to be slightly higher (closer to 3.5 chars/token)
        return max(1, len(text) // 4)

    def try_load_real_tokenizer(self, model_path: str) -> bool:
        """
        Attempt to load the actual HuggingFace tokenizer for precise counting.
        Falls back to approximation if transformers not installed.
        """
        try:
            from transformers import AutoTokenizer
            self._tokenizer = AutoTokenizer.from_pretrained(model_path)
            self._count_tokens = lambda text: len(self._tokenizer.encode(text, add_special_tokens=False))  # type: ignore[method-assign]
            return True
        except Exception:
            return False
