"""
Vibhu-Oska AI-OS — Structured Logger
High-performance structured logging with JSON and console output modes.

Uses structlog for structured context binding and rich for console rendering.
Every log entry carries: timestamp, level, source core/plugin, request_id,
and arbitrary context fields.
"""

from __future__ import annotations

import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import structlog
from structlog.types import Processor


class Logger:
    """
    Structured logging facility for the Vibhu-Oska AI-OS.

    Usage:
        log = Logger.get("CognitionCore")
        log.info("Model loaded", model_id="qwen2.5-3b", vram_used_gb=3.2)
        log.error("Inference failed", error=str(e), request_id=req.id)
    """

    _initialized: bool = False
    _log_dir: Path | None = None

    # ══════════════════════════════════════════════════════════════════════
    # Initialization
    # ══════════════════════════════════════════════════════════════════════

    @classmethod
    def initialize(
        cls,
        level: str = "DEBUG",
        fmt: str = "console",
        output_dir: str = "Log",
        file_enabled: bool = True,
        console_enabled: bool = True,
        project_root: Path | None = None,
    ) -> None:
        """
        Initialize the global logging configuration.
        Must be called once during system bootstrap.
        """
        if cls._initialized:
            return

        root = project_root or Path.cwd()
        cls._log_dir = root / output_dir
        cls._log_dir.mkdir(parents=True, exist_ok=True)

        # Build the structlog processor chain
        shared_processors: list[Processor] = [
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.UnicodeDecoder(),
        ]

        if fmt == "json":
            renderer = structlog.processors.JSONRenderer()
        else:
            renderer = structlog.dev.ConsoleRenderer(
                colors=True,
                pad_event_to=40,
            )

        structlog.configure(
            processors=[
                *shared_processors,
                structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
            ],
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )

        # Configure standard library logging
        formatter = structlog.stdlib.ProcessorFormatter(
            processors=[
                structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                renderer,
            ],
        )

        handlers: list[logging.Handler] = []

        if console_enabled:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(formatter)
            handlers.append(console_handler)

        if file_enabled:
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            log_file = cls._log_dir / f"vibhu_oska_{today}.log"
            file_handler = logging.FileHandler(log_file, encoding="utf-8")
            file_handler.setFormatter(
                structlog.stdlib.ProcessorFormatter(
                    processors=[
                        structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                        structlog.processors.JSONRenderer(),  # Always JSON in files
                    ],
                )
            )
            handlers.append(file_handler)

        root_logger = logging.getLogger()
        root_logger.handlers.clear()
        for handler in handlers:
            root_logger.addHandler(handler)
        root_logger.setLevel(getattr(logging, level.upper(), logging.DEBUG))

        cls._initialized = True

    # ══════════════════════════════════════════════════════════════════════
    # Logger Factory
    # ══════════════════════════════════════════════════════════════════════

    @classmethod
    def get(cls, name: str, **initial_context: Any) -> structlog.stdlib.BoundLogger:
        """
        Get a named, context-bound logger instance.

        Args:
            name: The logger name (usually the core/plugin name)
            **initial_context: Key-value pairs permanently bound to this logger

        Returns:
            A structlog BoundLogger with the given name and context
        """
        if not cls._initialized:
            # Auto-initialize with console defaults if not yet done
            cls.initialize(level="DEBUG", fmt="console", file_enabled=False)

        logger = structlog.get_logger(name)
        if initial_context:
            logger = logger.bind(**initial_context)
        return logger

    # ══════════════════════════════════════════════════════════════════════
    # Convenience Methods
    # ══════════════════════════════════════════════════════════════════════

    @classmethod
    def bind_request(cls, request_id: str) -> None:
        """Bind a request_id to all loggers in the current context (async-safe)."""
        structlog.contextvars.bind_contextvars(request_id=request_id)

    @classmethod
    def clear_context(cls) -> None:
        """Clear all context variables (call at end of request lifecycle)."""
        structlog.contextvars.clear_contextvars()
