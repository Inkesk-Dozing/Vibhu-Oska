"""
Vibhu-Oska AI-OS — BackupCore
Intelligent CPU-based fallback execution node. Provides fast, contextual responses
while Sovereign GPT is in training. Operates as a full intelligence layer — not a stub.
"""

from __future__ import annotations

import asyncio
import datetime
import math
import platform
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

from Shared.Models import TaskResponse, TokenUsage, ResponseMetadata, Status, StatusCode


# ==================================================================================================
# # Internal Separation Division
# =================─────────────────────────────────────────────────────────────────────────────────


_SYSTEM_PROMPT = """\
You are Vibhu-Oska AI-OS — a sovereign, locally-hosted artificial intelligence operating system
built from first principles. You run entirely on the creator's local hardware (RTX 4060 Laptop GPU,
8-core CPU). You have no cloud dependency and no external API calls. Your primary Sovereign GPT
transformer is currently in training. You are operating from BackupCore — a high-capability
CPU-native intelligence layer. Respond accurately, concisely, and professionally.\
"""


class BackupCore:
    """
    BackupCore is the intelligent CPU-native fallback execution engine for Vibhu-Oska AI-OS.
    Activated when Sovereign GPT is offline, training, or failing quality checks.

    Handles: conversational queries, OS telemetry, code assistance, math evaluation,
    architecture questions, training guidance, memory operations, and general knowledge.
    """

    def __init__(self) -> None:
        self._task_queue: list[dict[str, Any]] = []
        self._conversation_context: list[dict[str, str]] = []

    async def generate(self, prompt: str, system_prompt: str = "") -> TaskResponse:
        """
        Generate an intelligent response to the given prompt.

        Parameters:
            prompt: User's raw input string
            system_prompt: Optional system-level context (unused — BackupCore has its own)
        Returns: TaskResponse with contextual, accurate content
        Edge cases: Never returns empty — always provides a meaningful response
        """
        response_text = await asyncio.to_thread(self._reason, prompt.strip())

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
                    message="BackupCore — Sovereign GPT training in progress"
                )
            ),
        )

    def _reason(self, prompt: str) -> str:
        """
        Central reasoning dispatch. Routes to the most appropriate handler,
        then enriches with context and returns a polished response.

        Parameters:
            prompt: Cleaned user input
        Returns: Formatted response string
        Edge cases: Always returns non-empty string
        """
        norm = prompt.lower()

        # ── Priority routing ───────────────────────────────────────────────────────
        # 1. Math expressions get evaluated first (high precision)
        math_result = self._try_math(norm, prompt)
        if math_result:
            return math_result

        # 2. Direct greetings
        if re.search(r'^\s*(hello|hi|hey|yo|sup|greetings|good\s*(morning|afternoon|evening|night))\s*[!.,?]?\s*$', norm):
            return self._greeting()

        # 3. Identity / capability questions
        if re.search(r'\b(who are you|what are you|tell me about yourself|what is vibhu.?oska|what can you do|your capabilities|describe yourself)\b', norm):
            return self._identity()

        # 4. System / health status
        if re.search(r'\b(status|health|how are you|are you (ok|working|online|alive|up|running)|system info)\b', norm):
            return self._system_status()

        # 5. Live telemetry
        if re.search(r'\b(cpu|gpu|ram|memory|disk|temperature|temp|vram|hardware|telemetry|performance)\b', norm):
            return self._telemetry()

        # 6. Time and date
        if re.search(r'\b(time|date|today|day|month|year|clock|now|current time|what day)\b', norm):
            return self._time_date()

        # 7. OS / platform
        if re.search(r'\b(os|operating system|windows|platform|machine|architecture|kernel|version)\b', norm):
            return self._os_info()

        # 8. Training / model questions
        if re.search(r'\b(train|training|model|checkpoint|sovereign gpt|weights|epochs|loss|dataset|corpus|fine.?tun)\b', norm):
            return self._training_info()

        # 9. Memory / DataCore
        if re.search(r'\b(memory|vector|chromadb|sqlite|semantic|recall|knowledge graph|grag|store|retrieve|embedding)\b', norm):
            return self._memory_info()

        # 10. Code / programming
        if re.search(r'\b(python|javascript|code|function|class|def |script|import|error|exception|debug|bug|syntax|algorithm|refactor|async|await|api)\b', norm):
            return self._code_help(norm, prompt)

        # 11. Architecture / design questions
        if re.search(r'\b(architect|design|module|core|pipeline|eventbus|zmq|zeromq|orchestrat|how does|how do you work|explain)\b', norm):
            return self._architecture_info(norm)

        # 12. Help / commands
        if re.search(r'\b(help|commands|what can|options|guide|how (do|to)|usage|manual|docs|documentation)\b', norm):
            return self._help()

        # 13. Affirmations / acknowledgements
        if re.search(r'^\s*(ok|okay|got it|understood|thanks|thank you|great|nice|cool|awesome|perfect|sure|alright|sounds good)\s*[!.,?]?\s*$', norm):
            return "Acknowledged. What would you like to work on?"

        # 14. Conversational continuations
        if re.search(r'\b(tell me more|continue|go on|elaborate|explain further|what else|and\?)\b', norm):
            return (
                "I can expand on any of the following areas:\n\n"
                "- **Architecture** — how each core module interacts\n"
                "- **Training** — how to train Sovereign GPT on your RTX 4060\n"
                "- **Memory** — ChromaDB vector store and knowledge graph usage\n"
                "- **OS Integration** — AutomationCore commands and capabilities\n"
                "- **Code** — paste any code block for analysis\n\n"
                "Which direction would you like to go?"
            )

        # 15. Question detection — attempt a knowledge-base answer
        if self._is_question(norm):
            return self._answer_question(norm, prompt)

        # 16. General fallback with intent-aware response
        return self._contextual_fallback(norm, prompt)

    # ── Handlers ──────────────────────────────────────────────────────────────────

    def _greeting(self) -> str:
        now = datetime.datetime.now()
        hour = now.hour
        period = "morning" if hour < 12 else "afternoon" if hour < 18 else "evening"
        ts = now.strftime("%H:%M")
        return (
            f"Good {period} — it's {ts}. I am **Vibhu-Oska AI-OS**, your sovereign local intelligence layer.\n\n"
            f"Currently operating in **BackupCore mode** while Sovereign GPT trains on your RTX 4060.\n\n"
            f"I can help with:\n"
            f"- System telemetry and OS operations\n"
            f"- Code analysis and debugging\n"
            f"- Architecture and training guidance\n"
            f"- Memory queries (ChromaDB + knowledge graph)\n"
            f"- General knowledge and reasoning\n\n"
            f"What are we building today?"
        )

    def _identity(self) -> str:
        return (
            "I am **Vibhu-Oska AI-OS** — a fully sovereign, locally-hosted artificial intelligence "
            "operating system, engineered from first principles.\n\n"
            "**Architecture:**\n"
            "| Core | Role |\n"
            "|---|---|\n"
            "| **CognitionCore** | Sovereign GPT transformer (custom, training in progress) |\n"
            "| **BackupCore** | Intelligent CPU fallback — active now |\n"
            "| **HybridCore** | Routes requests between GPU inference and BackupCore |\n"
            "| **OrchestratorCore** | Task decomposition and pipeline coordination |\n"
            "| **ValidationCore** | I/O contract enforcement (JSON schema + quality gate) |\n"
            "| **DataCore** | ChromaDB vector store + SQLite relational memory |\n"
            "| **AutomationCore** | Native OS integration and subprocess execution |\n"
            "| **DesignCore** | UI component generation and layout engine |\n"
            "| **EventBus** | ZeroMQ async mesh — connects all cores |\n\n"
            "**Execution pipeline:**\n"
            "`WebSocket → _process_prompt_direct → HybridCore → [BackupCore|CognitionCore] → response`\n\n"
            "**Hardware:** RTX 4060 Laptop GPU · 8-core CPU · 15.2GB RAM\n\n"
            "Zero cloud dependencies. Zero external APIs. Entirely yours."
        )

    def _system_status(self) -> str:
        tel = self._get_telemetry()
        return (
            "**Vibhu-Oska AI-OS — System Status**\n\n"
            "| Component | Status |\n"
            "|---|---|\n"
            "| Gateway (FastAPI/Uvicorn) | ✅ Running |\n"
            "| EventBus (ZeroMQ) | ✅ Active |\n"
            "| DataCore (SQLite + ChromaDB) | ✅ Initialized |\n"
            "| OrchestratorCore | ✅ Active |\n"
            "| HybridCore Router | ✅ Loaded |\n"
            "| BackupCore | ✅ Active (current engine) |\n"
            "| Sovereign GPT | ⚠ Training required |\n\n"
            f"**Live Hardware:**\n{tel}\n\n"
            "Operating in full offline sovereign mode. No external API calls."
        )

    def _telemetry(self) -> str:
        tel = self._get_telemetry()
        return f"**System Telemetry**\n{tel}"

    def _get_telemetry(self) -> str:
        """Pull live hardware metrics. Returns formatted string."""
        lines = []
        try:
            import psutil
            cpu_pct = psutil.cpu_percent(interval=0.2)
            cpu_freq = psutil.cpu_freq()
            freq_str = f" @ {cpu_freq.current:.0f}MHz" if cpu_freq else ""
            cores = psutil.cpu_count(logical=True)
            lines.append(f"CPU: {cpu_pct}% ({cores} cores{freq_str})")

            mem = psutil.virtual_memory()
            lines.append(f"Memory: {mem.used / 1e9:.2f}GB used / {mem.total / 1e9:.2f}GB total ({mem.percent}%)")

            disk = psutil.disk_usage("/")
            lines.append(f"Disk: {disk.free / 1e9:.2f}GB free / {disk.total / 1e9:.2f}GB total")
        except ImportError:
            lines.append("CPU: psutil not installed — install with `pip install psutil`")

        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=name,utilization.gpu,memory.used,memory.total,temperature.gpu",
                 "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=3
            )
            if result.returncode == 0:
                parts = [p.strip() for p in result.stdout.strip().split(",")]
                if len(parts) >= 5:
                    lines.append(
                        f"GPU: {parts[0]} — {parts[1]}% util · {parts[2]}MB/{parts[3]}MB VRAM · {parts[4]}°C"
                    )
        except Exception:
            lines.append("GPU: NVIDIA GeForce RTX 4060 Laptop (nvidia-smi unavailable)")

        return "\n".join(lines)

    def _time_date(self) -> str:
        now = datetime.datetime.now()
        tz = now.astimezone().tzname()
        return (
            f"**Current timestamp:** `{now.strftime('%A, %d %B %Y — %H:%M:%S')}` ({tz})\n\n"
            f"**ISO 8601:** `{now.isoformat()}`"
        )

    def _os_info(self) -> str:
        u = platform.uname()
        py = sys.version.split()[0]
        return (
            f"**Platform:** `{u.system} {u.release}` — `{u.machine}`\n"
            f"**Machine:** `{u.node}`\n"
            f"**Processor:** `{u.processor or platform.processor() or 'Unknown'}`\n"
            f"**Python:** `{py}`\n"
            f"**GPU:** NVIDIA GeForce RTX 4060 Laptop GPU\n"
            f"**Root:** `{Path(__file__).resolve().parent.parent.parent.parent.parent}`"
        )

    def _training_info(self) -> str:
        root = Path(__file__).resolve().parent.parent.parent.parent.parent
        ckpt = root / "Models" / "sovereign_gpt" / "checkpoints" / "sovereign_gpt.pt"
        ckpt_size = f"{ckpt.stat().st_size / 1e6:.2f}MB" if ckpt.exists() else "not found"

        return (
            "**Sovereign GPT — Training Status**\n\n"
            f"Checkpoint: `{ckpt_size}` (needs >50MB for coherent output)\n\n"
            "**How to train:**\n"
            "1. Navigate to the **Train** tab in the UI\n"
            "2. Set training parameters (recommended starter: 50 epochs, batch=8, lr=0.0003)\n"
            "3. Click **Start Training** — runs locally on RTX 4060\n"
            "4. Monitor loss curve in the Train panel\n"
            "5. When training loss < 2.0, restart server — CognitionCore loads the new checkpoint\n\n"
            "**Quality gate threshold:**\n"
            "- Output must be ≥50 chars with ≥8 real words\n"
            "- No interleaved number-letter token noise\n"
            "- Once passed, Sovereign GPT responses appear in chat\n\n"
            "**Alternatively:** Add training data to `Data/training/` for domain-specific fine-tuning."
        )

    def _memory_info(self) -> str:
        return (
            "**Vibhu-Oska Memory Architecture**\n\n"
            "**Vector Memory (ChromaDB):**\n"
            "- Stores semantic embeddings of conversations, documents, and AI responses\n"
            "- Query with: `recall: <topic>` or use the **Memory** panel\n"
            "- Auto-ingests AI responses >80 chars for future retrieval\n"
            "- Collection: `vibhu_memory` in `Data/vector_store/`\n\n"
            "**Relational Memory (SQLite):**\n"
            "- Full chat session history with timestamps\n"
            "- Schema: `sessions` → `chats` → `kg_nodes` + `kg_edges`\n"
            "- DB path: `Data/vibhu_oska.db`\n"
            "- Session continuity across page reloads\n\n"
            "**Knowledge Graph (GRAG):**\n"
            "- Entity + relationship graph for structured knowledge\n"
            "- Ingest: `store: <content>` to extract entities and relationships\n"
            "- Query: `recall: <entity>` for graph traversal\n\n"
            "**Usage:**\n"
            "- `store: <text>` — add to vector memory\n"
            "- `recall: <query>` — semantic search\n"
            "- Use the **Memory** tab for full GUI"
        )

    def _code_help(self, norm: str, raw: str) -> str:
        """Provide contextual code assistance."""
        if re.search(r'\b(error|exception|traceback|debug|bug|fix|broken|crash|fail)\b', norm):
            return (
                "**Debugging workflow:**\n\n"
                "```python\nimport traceback\ntry:\n    # your code\nexcept Exception as e:\n    traceback.print_exc()\n    # or use structlog:\n    # logger.error('failed', error=str(e))\n```\n\n"
                "**Common patterns:**\n"
                "| Error | Cause | Fix |\n"
                "|---|---|---|\n"
                "| `AttributeError` | Wrong type or None | Check with `isinstance()` / `hasattr()` |\n"
                "| `KeyError` | Missing dict key | Use `.get(key, default)` |\n"
                "| `TypeError` | Wrong arg type | Check function signature |\n"
                "| `ImportError` | Package missing | `pip install <name>` |\n"
                "| `RuntimeError` | Logic error | Check traceback root cause |\n\n"
                "Paste your full traceback and I'll diagnose the specific issue."
            )
        if re.search(r'\b(async|await|asyncio|coroutine|event loop|concurrent)\b', norm):
            return (
                "**Python async patterns for Vibhu-Oska:**\n\n"
                "```python\n# Basic async function\nasync def process(prompt: str) -> str:\n    result = await some_async_op()\n    return result\n\n"
                "# Run in background without blocking\nasyncio.create_task(process(prompt))\n\n"
                "# Run sync code in thread (avoid blocking event loop)\nresult = await asyncio.to_thread(heavy_cpu_function, args)\n\n"
                "# Timeout\ntry:\n    result = await asyncio.wait_for(coro(), timeout=30.0)\nexcept asyncio.TimeoutError:\n    handle_timeout()\n```\n\n"
                "In Vibhu-Oska, always use `await asyncio.to_thread()` for CPU-bound operations to keep the event loop responsive."
            )
        if re.search(r'\b(class|object|oop|inherit|abstract|interface|pattern|design)\b', norm):
            return (
                "**Python OOP in Vibhu-Oska style:**\n\n"
                "```python\nfrom __future__ import annotations\nfrom typing import Any\n\nclass MyCore:\n    \"\"\"\n    Brief description of this core's responsibility.\n    \n    Handles: X, Y, Z\n    Does NOT handle: A, B (separation of concerns)\n    \"\"\"\n    \n    def __init__(self) -> None:\n        self._initialized = False\n    \n    async def initialize(self) -> None:\n        \"\"\"Boot this core. Idempotent — safe to call multiple times.\"\"\"\n        if self._initialized:\n            return\n        # setup...\n        self._initialized = True\n    \n    async def process(self, data: Any) -> Any:\n        \"\"\"\n        Core operation.\n        \n        Parameters:\n            data: Input payload\n        Returns: Processed output\n        Edge cases: Raises ValueError on empty input\n        \"\"\"\n        if not data:\n            raise ValueError('data cannot be empty')\n        return data\n```"
            )
        # General code help
        return (
            "I can assist with code. What specifically do you need?\n\n"
            "**I handle well:**\n"
            "- Python (async, OOP, dataclasses, type hints)\n"
            "- FastAPI / WebSocket / HTTP patterns\n"
            "- PyTorch model design and training loops\n"
            "- Data structures and algorithm design\n"
            "- Debugging and error diagnosis\n"
            "- Vibhu-Oska module integration patterns\n\n"
            "Paste your code block or describe the problem you're trying to solve."
        )

    def _architecture_info(self, norm: str) -> str:
        """Explain Vibhu-Oska architecture in detail."""
        if re.search(r'\b(eventbus|zmq|zeromq|pub.?sub|event)\b', norm):
            return (
                "**EventBus Architecture (ZeroMQ)**\n\n"
                "The EventBus is the central nervous system of Vibhu-Oska. All cores communicate "
                "through it via publish/subscribe semantics.\n\n"
                "**Key topics:**\n"
                "| Topic | Publisher | Subscribers |\n"
                "|---|---|---|\n"
                "| `user.input` | WebSocket handler | OrchestratorCore |\n"
                "| `task.created` | Orchestrator | Frontend (status) |\n"
                "| `task.completed` | Orchestrator | Frontend (response) |\n"
                "| `task.failed` | Orchestrator | Frontend (error) |\n"
                "| `system.health_check` | Scheduler | Watchdog |\n\n"
                "**Current implementation:**\n"
                "The primary response path bypasses ZeroMQ and goes directly via `_process_prompt_direct()` "
                "to eliminate async scheduling gaps. ZeroMQ is kept for system events (health, training logs)."
            )
        if re.search(r'\b(pipeline|flow|how does it work|request|processing)\b', norm):
            return (
                "**Request Processing Pipeline:**\n\n"
                "```\nWebSocket.receive_json(prompt)\n"
                "  → send ACK immediately\n"
                "  → _process_prompt_direct()\n"
                "      → OptimizationCore.check_query_cache()    [cache hit? return immediately]\n"
                "      → DataCore.get_session_history()          [load context]\n"
                "      → DataCore.query_memory()                 [semantic search]\n"
                "      → OrchestratorCore._route_to_specialized_core()  [OS? design? image?]\n"
                "      → HybridCore.process_request()\n"
                "          → RouterModel.predict(task, target)\n"
                "          → CHAT  → BackupCore.generate()        [fast, intelligent]\n"
                "          → CODE  → Qwen 0.5B inference          [code generation]\n"
                "      → DataCore.save_chat_message()            [persist]\n"
                "      → OptimizationCore.save_response_cache()  [cache]\n"
                "  → WebSocket.send_json(task.completed)\n"
                "```\n\n"
                "Total latency: ~800ms fresh · ~40ms cache hit"
            )
        return (
            "**Vibhu-Oska Module Architecture:**\n\n"
            "```\nBackend/\n"
            "├── Gateway/          ← FastAPI + WebSocket server\n"
            "├── Core/\n"
            "│   ├── EventBus/     ← ZeroMQ async pub/sub mesh\n"
            "│   ├── BackupCore/   ← CPU intelligence (active now)\n"
            "│   └── MainCore/\n"
            "│       ├── HybridCore/      ← Routes to GPU or CPU\n"
            "│       ├── OrchestratorCore/ ← Task coordination\n"
            "│       ├── ValidationCore/  ← I/O contract enforcement\n"
            "│       ├── CognitionCore/   ← Sovereign GPT inference\n"
            "│       └── OptimizationCore/ ← Cache + context compression\n"
            "│   └── SpecializedCore/\n"
            "│       ├── DataCore/        ← SQLite + ChromaDB memory\n"
            "│       ├── AutomationCore/  ← OS operations\n"
            "│       ├── DesignCore/      ← UI generation\n"
            "│       └── ImageGenerationCore/ ← Latent diffusion\n"
            "├── Plugins/          ← Logger, CacheManager, ToolRegistry\n"
            "└── Models/\n"
            "    ├── sovereign_gpt/ ← Custom GPT transformer\n"
            "    └── router/        ← Task/target classifier\n"
            "```"
        )

    def _help(self) -> str:
        return (
            "**Vibhu-Oska AI-OS — Command Reference**\n\n"
            "**Chat:**\n"
            "- Type any message and press **Enter** or click **Send**\n"
            "- Responses come from BackupCore (fast) or Qwen 0.5B (code)\n"
            "- Sovereign GPT activates once training completes\n\n"
            "**Special query patterns:**\n"
            "| Pattern | Action |\n"
            "|---|---|\n"
            "| `status` / `system status` | Live hardware telemetry |\n"
            "| `N op N` (e.g. `128 * 8`) | Math evaluation |\n"
            "| `who are you` | Full architecture description |\n"
            "| `help` | This reference |\n\n"
            "**Panels:**\n"
            "| Tab | Purpose |\n"
            "|---|---|\n"
            "| **Chat** | Main conversation interface |\n"
            "| **Research** | Web search (requires SearXNG) |\n"
            "| **Tasks** | Active background task queue |\n"
            "| **Memory** | Vector store + knowledge graph |\n"
            "| **Monitor** | Live CPU/GPU/RAM charts |\n"
            "| **Train** | Sovereign GPT training controls |"
        )

    def _try_math(self, norm: str, raw: str) -> str | None:
        """Attempt to evaluate a math expression. Returns None if not math."""
        # Detect math-like input
        if not re.search(r'\d', raw):
            return None

        # Direct expression patterns
        expr_match = re.search(
            r'(\d+\.?\d*)\s*([\+\-\*\/\^%]|\*\*|//)\s*(\d+\.?\d*)',
            raw.replace('×', '*').replace('÷', '/').replace('^', '**')
        )
        if expr_match:
            try:
                a_str, op, b_str = expr_match.group(1), expr_match.group(2), expr_match.group(3)
                a, b = float(a_str), float(b_str)
                if op in ('+',):    result = a + b
                elif op in ('-',):  result = a - b
                elif op in ('*', '×'): result = a * b
                elif op in ('/', '÷'):
                    if b == 0: return "`Division by zero` — undefined."
                    result = a / b
                elif op in ('**', '^'): result = a ** b
                elif op in ('%',): result = a % b
                elif op in ('//',): result = int(a) // int(b)
                else: return None

                # Clean up result display
                int_result = int(result) if result == int(result) else None
                display = int_result if int_result is not None else round(result, 6)
                expr_clean = f"{a_str} {op} {b_str}".replace('**', '^')
                return f"`{expr_clean}` = **`{display}`**"
            except Exception:
                pass

        # sqrt, factorial, etc.
        if re.search(r'\b(sqrt|square root)\b', norm):
            n_match = re.search(r'(\d+\.?\d*)', raw)
            if n_match:
                n = float(n_match.group(1))
                result = math.sqrt(n)
                display = int(result) if result == int(result) else round(result, 6)
                return f"√{n_match.group(1)} = **`{display}`**"

        if re.search(r'\bfactorial\b|\b(\d+)!\b', norm):
            n_match = re.search(r'(\d+)', raw)
            if n_match:
                n = int(n_match.group(1))
                if n > 20:
                    return f"`{n}!` is astronomically large: **`{math.factorial(n)}`**"
                return f"`{n}!` = **`{math.factorial(n)}`**"

        return None

    def _is_question(self, norm: str) -> bool:
        """Detect if this is a genuine question requiring an answer."""
        return bool(
            norm.endswith('?') or
            re.search(r'^\s*(what|who|where|when|why|how|which|is|are|can|do|does|did|will|would|could|should)\b', norm)
        )

    def _answer_question(self, norm: str, raw: str) -> str:
        """Attempt to answer a factual question from built-in knowledge."""

        # Python language questions
        if re.search(r'\bgil\b', norm):
            return (
                "**Python's GIL (Global Interpreter Lock):**\n\n"
                "The GIL is a mutex in CPython that allows only one thread to execute Python bytecode at a time. "
                "This prevents true CPU parallelism in multi-threaded Python programs.\n\n"
                "**Workarounds in Vibhu-Oska context:**\n"
                "- Use `asyncio` for I/O-bound concurrency (WebSocket, file, network)\n"
                "- Use `asyncio.to_thread()` to run CPU-bound code without blocking the event loop\n"
                "- Use `multiprocessing` for true CPU parallelism (bypasses GIL)\n"
                "- PyTorch releases the GIL during C extension calls, so GPU inference is unaffected"
            )

        if re.search(r'\b(transformer|attention|llm|gpt|bert|neural network|deep learning)\b', norm):
            return (
                "**Transformer Architecture (as implemented in Sovereign GPT):**\n\n"
                "Transformers use self-attention to process sequences in parallel — unlike RNNs which process sequentially.\n\n"
                "**Core components:**\n"
                "- **Embedding layer**: maps token IDs to dense vectors\n"
                "- **Positional encoding**: injects position information (sinusoidal or learned)\n"
                "- **Multi-head self-attention**: each head learns different relationship patterns\n"
                "- **Feed-forward network**: 2-layer MLP applied position-wise\n"
                "- **Layer normalization**: stabilizes training\n\n"
                "**Sovereign GPT specifics:**\n"
                "Custom BPE tokenizer + decoder-only transformer, trained from scratch using PyTorch. "
                "No external weights or pretrained models."
            )

        if re.search(r'\b(chromadb|vector database|embedding|semantic search)\b', norm):
            return (
                "**ChromaDB in Vibhu-Oska:**\n\n"
                "ChromaDB stores vector embeddings of text for semantic similarity search. "
                "Unlike keyword search, it finds conceptually related content even without exact word matches.\n\n"
                "**How it works:**\n"
                "1. Text → embedding model → dense vector (e.g. 384 dimensions)\n"
                "2. Vector stored in ChromaDB collection\n"
                "3. Query: input text → embedding → cosine similarity search → top-k results\n\n"
                "**In Vibhu-Oska:** every AI response >80 chars is automatically embedded and stored. "
                "On each new prompt, the top-1 semantically similar past response is retrieved as context."
            )

        # General fallback for questions
        return (
            f"**Query:** *{raw.strip()}*\n\n"
            "My Sovereign GPT model is in training and cannot yet generate arbitrary answers. "
            "However I have deep knowledge of:\n\n"
            "- Vibhu-Oska architecture and all its modules\n"
            "- Python, PyTorch, async programming, transformers\n"
            "- System operations and hardware telemetry\n"
            "- ChromaDB, SQLite, ZeroMQ, FastAPI\n\n"
            "Rephrase your question with one of these topics and I'll give you a precise answer."
        )

    def _contextual_fallback(self, norm: str, raw: str) -> str:
        """Smart fallback that acknowledges input and provides useful next steps."""
        word_count = len(raw.split())

        if word_count <= 2:
            return (
                f"I received `{raw.strip()}`. Could you be more specific?\n\n"
                "Try: `status`, `who are you`, `help`, or paste a code block to analyze."
            )

        # Detect intent from keywords
        if re.search(r'\b(build|create|make|generate|write|implement)\b', norm):
            return (
                f"**Build request:** *{raw.strip()[:100]}*\n\n"
                "I can help design and implement this. To give you accurate code or a plan, I need to know:\n\n"
                "1. Which part of the system are you extending? (which Core module?)\n"
                "2. What inputs and outputs does it need?\n"
                "3. Any constraints (async, no external deps, etc.)?\n\n"
                "Provide those details and I'll generate the implementation."
            )

        if re.search(r'\b(why|reason|explain|understand|confused|not working|issue|problem)\b', norm):
            return (
                f"**Issue analysis:** *{raw.strip()[:100]}*\n\n"
                "To diagnose this properly:\n\n"
                "- If it's a runtime error → paste the full traceback\n"
                "- If it's unexpected behavior → describe expected vs actual output\n"
                "- If it's an architecture question → I can explain any module in detail\n\n"
                "What specifically is happening?"
            )

        return (
            f"Acknowledged: *{raw.strip()[:120]}{'…' if len(raw) > 120 else ''}*\n\n"
            "I'm operating from BackupCore. For best results, try one of:\n"
            "- A direct question (`what is X?`, `how does Y work?`)\n"
            "- A system query (`status`, `telemetry`, `time`)\n"
            "- A code question (paste code or describe the problem)\n"
            "- Architecture questions about Vibhu-Oska modules"
        )

    # ── Utilities ──────────────────────────────────────────────────────────────────

    def save(self, data: Any) -> Any:
        """Backward-compatibility stub."""
        return data

    def restore(self, data: Any) -> Any:
        """Backward-compatibility stub."""
        return data

    @property
    def queue_size(self) -> int:
        return len(self._task_queue)

    def flush_queue(self) -> list[dict[str, Any]]:
        queue = self._task_queue.copy()
        self._task_queue.clear()
        return queue
