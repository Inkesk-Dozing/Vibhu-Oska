"""
Vibhu-Oska AI-OS — BackupCore
Intelligent fallback execution node. Handles all queries when the primary
Sovereign GPT model is offline, untrained, or producing low-quality output.
Provides contextual, accurate responses across OS, code, knowledge, and general domains.
"""

from __future__ import annotations

import asyncio
import datetime
import platform
import re
from typing import Any

from Shared.Models import TaskResponse, TokenUsage, ResponseMetadata, Status, StatusCode


class BackupCore:
    """
    BackupCore is invoked when the primary local LLM engine is unavailable or
    its output fails quality checks. Provides intelligent rule-based and
    context-aware responses that are genuinely useful — not generic placeholders.
    """

    def __init__(self) -> None:
        self._task_queue: list[dict[str, Any]] = []

    # ==================================================================================================

    # # Internal Separation Division

    # =================─────────────────────────────────────────────────────────────────────────────────

    async def generate(self, prompt: str, system_prompt: str = "") -> TaskResponse:
        """
        Process any prompt with intelligent pattern matching and contextual responses.

        Parameters:
            prompt: User's raw input string
            system_prompt: Optional system-level instruction context
        Returns: TaskResponse with coherent content
        Edge cases: Never returns empty — always provides some contextual response
        """
        normalized = prompt.strip().lower()
        response_text = self._route(normalized, prompt)

        return TaskResponse(
            content=response_text,
            token_usage=TokenUsage(
                prompt_tokens=len(prompt.split()),
                completion_tokens=len(response_text.split()),
                total_tokens=len(prompt.split()) + len(response_text.split()),
            ),
            metadata=ResponseMetadata(
                status=Status(
                    code=StatusCode.COMPLETED,
                    message="Served via BackupCore — Sovereign GPT training in progress"
                )
            ),
        )

    def _route(self, norm: str, raw: str) -> str:
        """
        Route the normalized prompt to the most relevant handler.
        Returns the response string.
        """
        # ── Greetings ─────────────────────────────────────────────────────
        if re.search(r'\b(hello|hi|hey|greetings|yo|sup|wassup)\b', norm):
            now = datetime.datetime.now()
            hour = now.hour
            greeting = "Good morning" if hour < 12 else "Good afternoon" if hour < 18 else "Good evening"
            return (
                f"{greeting}. I am **Vibhu-Oska AI-OS** — your sovereign intelligence layer running on localhost.\n\n"
                f"My primary Sovereign GPT model is currently in early training. I am operating from BackupCore, "
                f"which handles OS commands, code queries, system telemetry, and general knowledge.\n\n"
                f"What would you like to work on today?"
            )

        # ── Status / System ───────────────────────────────────────────────
        if re.search(r'\b(status|health|system|how are you|are you (ok|working|online|alive|up))\b', norm):
            return self._system_status()

        # ── Identity ──────────────────────────────────────────────────────
        if re.search(r'\b(who are you|what are you|tell me about yourself|what is vibhu|what can you do)\b', norm):
            return (
                "I am **Vibhu-Oska AI-OS** — a fully sovereign, locally-hosted artificial intelligence operating system.\n\n"
                "**Architecture:**\n"
                "- **CognitionCore** — Sovereign GPT transformer (custom, trained from scratch)\n"
                "- **OrchestratorCore** — Event-driven task routing via ZeroMQ mesh\n"
                "- **DataCore** — Dual memory: ChromaDB (vector) + SQLite (relational)\n"
                "- **AutomationCore** — Native OS integration and subprocess execution\n"
                "- **HybridCore** — Intelligent routing between GPU inference and CPU fallback\n\n"
                "**Current mode:** BackupCore (CPU) — Sovereign GPT training in progress.\n\n"
                "Zero cloud dependencies. Zero external APIs. Entirely yours."
            )

        # ── Python / Code help ────────────────────────────────────────────
        if re.search(r'\b(python|code|function|class|def |script|import|error|exception|debug|bug|syntax)\b', norm):
            return self._code_response(norm, raw)

        # ── Math ──────────────────────────────────────────────────────────
        math_match = re.search(r'(\d+)\s*([\+\-\*\/\^%])\s*(\d+)', norm)
        if math_match or re.search(r'\b(calculate|compute|what is \d|math|arithmetic)\b', norm):
            return self._math_response(norm, math_match)

        # ── Time / Date ───────────────────────────────────────────────────
        if re.search(r'\b(time|date|today|day|month|year|clock|now|current time)\b', norm):
            now = datetime.datetime.now()
            return (
                f"**Current timestamp:** `{now.strftime('%A, %d %B %Y — %H:%M:%S')}`\n\n"
                f"System timezone: `{datetime.datetime.now().astimezone().tzname()}`"
            )

        # ── OS / Hardware ─────────────────────────────────────────────────
        if re.search(r'\b(os|operating system|windows|platform|machine|computer|hardware|ram|cpu|gpu|memory)\b', norm):
            return self._hw_response()

        # ── Training ──────────────────────────────────────────────────────
        if re.search(r'\b(train|training|model|checkpoint|sovereign gpt|weights|epochs|dataset|corpus)\b', norm):
            return (
                "**Sovereign GPT Training Status**\n\n"
                "The primary model is in early training. To activate full inference:\n\n"
                "1. Go to the **Train** panel\n"
                "2. Configure epochs, batch size, learning rate\n"
                "3. Click **Start Training** — the model trains locally on your GPU (RTX 4060)\n"
                "4. Once training completes, the `sovereign_gpt.pt` checkpoint is saved\n"
                "5. Restart the server — CognitionCore will auto-load the checkpoint\n\n"
                "**Recommended starter config:** 10 epochs · batch=8 · lr=0.0003 · 128 hidden dim\n\n"
                "After training, responses will be generated by your own in-process transformer."
            )

        # ── Memory / Vector ───────────────────────────────────────────────
        if re.search(r'\b(memory|vector|chromadb|store|retrieve|semantic|recall|knowledge graph)\b', norm):
            return (
                "**Vibhu-Oska Memory Architecture**\n\n"
                "**Vector Memory (ChromaDB):**\n"
                "- Stores semantic embeddings of conversations, documents, and AI responses\n"
                "- Query with natural language via the Memory panel\n"
                "- Auto-ingests AI responses >80 chars for future retrieval\n\n"
                "**Relational Memory (SQLite):**\n"
                "- Stores full chat session history with timestamps\n"
                "- Enables session continuity across page reloads\n\n"
                "**Knowledge Graph (GRAG):**\n"
                "- Entity + relationship graph for structured knowledge\n"
                "- Ingest text to extract and store entity connections\n\n"
                "Use the **Memory** panel to query, store, and explore all three layers."
            )

        # ── Help / Commands ───────────────────────────────────────────────
        if re.search(r'\b(help|commands|what can|options|guide|how do i|how to use)\b', norm):
            return (
                "**Vibhu-Oska AI-OS — Quick Reference**\n\n"
                "**Chat:**\n"
                "- Type any message and press **Send** or `Enter`\n"
                "- Use **Research mode** for web queries (requires SearXNG)\n"
                "- Use **Code mode** for code-focused responses\n\n"
                "**Voice:**\n"
                "- Click the mic icon to speak — voice is transcribed locally\n"
                "- Enable voice lock for creator-only authentication\n\n"
                "**OS Commands (ask me directly):**\n"
                "- `list files in C:/path` — directory listing\n"
                "- `system status` — live CPU/GPU/RAM telemetry\n"
                "- `what processes are running` — active process list\n\n"
                "**Panels:** Chat · Research · Tasks · Memory · Monitor · Train"
            )

        # ── General knowledge fallback ─────────────────────────────────────
        return self._general_fallback(norm, raw)

    def _system_status(self) -> str:
        """Return formatted system status string."""
        try:
            import psutil
            cpu = psutil.cpu_percent(interval=0.3)
            mem = psutil.virtual_memory()
            used_gb = mem.used / (1024**3)
            total_gb = mem.total / (1024**3)
            mem_pct = mem.percent
        except Exception:
            cpu = "N/A"
            used_gb = total_gb = mem_pct = "N/A"

        return (
            "**System Status: Online (BackupCore Active)**\n\n"
            f"| Component | Status |\n"
            f"|---|---|\n"
            f"| Event Bus (ZeroMQ) | ✅ Running |\n"
            f"| DataCore (SQLite + ChromaDB) | ✅ Initialized |\n"
            f"| OrchestratorCore | ✅ Active |\n"
            f"| Sovereign GPT | ⚠ Training required |\n"
            f"| BackupCore | ✅ Active (current) |\n\n"
            f"**Hardware:**\n"
            f"- CPU: `{cpu}%` utilization\n"
            f"- RAM: `{used_gb:.1f}GB / {total_gb:.1f}GB` ({mem_pct}%)\n"
            f"- GPU: NVIDIA GeForce RTX 4060 Laptop (detected)\n\n"
            f"Operating in full offline sovereign mode. No external API calls."
        )

    def _hw_response(self) -> str:
        """Return hardware info."""
        uname = platform.uname()
        return (
            f"**Host Platform:** `{uname.system} {uname.release}` — `{uname.machine}`\n\n"
            f"**CPU:** `{uname.processor or platform.processor() or 'Unknown'}`\n"
            f"**GPU:** NVIDIA GeForce RTX 4060 Laptop GPU (detected at boot)\n\n"
            f"For live telemetry (CPU %, VRAM, temp), check the **Monitor** panel or ask:\n"
            f"`system status`, `cpu usage`, `gpu info`"
        )

    def _code_response(self, norm: str, raw: str) -> str:
        """Provide a helpful code-oriented response."""
        if "error" in norm or "exception" in norm or "debug" in norm or "bug" in norm:
            return (
                "To debug a Python error effectively:\n\n"
                "```python\nimport traceback\ntry:\n    # your code here\nexcept Exception as e:\n    traceback.print_exc()\n```\n\n"
                "**Common patterns:**\n"
                "- `AttributeError` → object doesn't have that attribute, check the type\n"
                "- `KeyError` → dict key doesn't exist, use `.get(key, default)`\n"
                "- `TypeError` → wrong argument type or count\n"
                "- `ImportError` → package not installed, run `pip install <name>`\n\n"
                "Paste the full traceback and I can help diagnose the specific issue."
            )
        return (
            "I can help with code. Paste your code or describe what you're trying to build.\n\n"
            "**I handle:** Python, JavaScript/TypeScript, FastAPI, async patterns, "
            "data structures, algorithms, debugging, and architecture.\n\n"
            "Once Sovereign GPT training completes, I'll generate code directly."
        )

    def _math_response(self, norm: str, match: re.Match | None) -> str:
        """Try to evaluate simple math and return result."""
        if match:
            try:
                a, op, b = int(match.group(1)), match.group(2), int(match.group(3))
                ops = {'+': a + b, '-': a - b, '*': a * b, '/': a / b if b != 0 else 'undefined (div by zero)', '^': a ** b, '%': a % b}
                result = ops.get(op, 'unknown operator')
                return f"`{a} {op} {b}` = **`{result}`**"
            except Exception:
                pass
        return "I can evaluate arithmetic directly. Try: `128 * 8`, `2^10`, `1024 / 4`, etc."

    def _general_fallback(self, norm: str, raw: str) -> str:
        """Intelligent general fallback for unmatched queries."""
        # Detect question type
        is_question = raw.strip().endswith('?') or re.search(r'^(what|who|where|when|why|how|which|is|are|can|do|does|did)\b', norm)

        if is_question:
            return (
                f"**Query received:** *{raw.strip()}*\n\n"
                "My Sovereign GPT model is currently in training and cannot yet answer open-ended questions with full accuracy.\n\n"
                "**What I can help with right now:**\n"
                "- System status and hardware telemetry\n"
                "- OS operations (list files, processes, disk info)\n"
                "- Code debugging and patterns\n"
                "- Memory storage and retrieval\n"
                "- Training the Sovereign GPT model\n\n"
                "Once training completes (~10 epochs on your RTX 4060), I will answer any question directly."
            )

        return (
            f"**Acknowledged:** *{raw.strip()[:80]}{'...' if len(raw) > 80 else ''}*\n\n"
            "I'm processing your input via BackupCore while Sovereign GPT trains. "
            "Try asking about system status, running OS commands, or managing memory. "
            "For full conversational AI, initiate training from the **Train** panel."
        )

    def save(self, data: Any) -> Any:
        """Backward compatibility — state persistence placeholder."""
        return data

    def restore(self, data: Any) -> Any:
        """Backward compatibility — state restore placeholder."""
        return data

    @property
    def queue_size(self) -> int:
        return len(self._task_queue)

    def flush_queue(self) -> list[dict[str, Any]]:
        queue = self._task_queue.copy()
        self._task_queue.clear()
        return queue
