"""
Vibhu-Oska AI-OS — System Entry Point
═══════════════════════════════════════

The master bootstrap that brings the entire AI Operating Layer online.

Boot sequence:
    1. Load configuration (YAML + env overrides)
    2. Initialize structured logging
    3. Start the ZeroMQ event bus
    4. Initialize the Dynamic Tool Registry
    5. Register core plugins (Logger, ConfigLoader)
    6. Launch the FastAPI gateway
    7. System is LIVE

Usage:
    python -m Backend.EntryPoint
    # or
    vibhu-oska  (via pyproject.toml script entry)
"""

from __future__ import annotations

import sys
from pathlib import Path


def main() -> None:
    """Main entry point for the Vibhu-Oska AI-OS."""
    import sys
    import asyncio
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    import uvicorn

    from Backend.Plugins.ConfigLoader.ConfigLoader import ConfigLoader
    from Backend.Plugins.Logger.Logger import Logger

    # ── Resolve project root ──
    project_root = Path(__file__).resolve().parent.parent

    # ── Load configuration ──
    config = ConfigLoader.load(project_root=project_root)

    # ── Initialize logging ──
    log_config = config.get_section("logging")
    Logger.initialize(
        level=log_config.get("level", "DEBUG"),
        fmt=log_config.get("format", "console"),
        output_dir=log_config.get("output_dir", "Log"),
        file_enabled=log_config.get("file_enabled", True),
        console_enabled=log_config.get("console_enabled", True),
        project_root=project_root,
    )

    log = Logger.get("EntryPoint")

    # ── Banner ──
    log.info("=" * 60)
    log.info("  Vibhu-Oska AI-OS")
    log.info(f"  Version: {config.get('system.version', 'unknown')}")
    log.info(f"  Codename: {config.get('system.codename', 'unknown')}")
    log.info(f"  Environment: {config.environment}")
    log.info(f"  Tier: {config.get('system.tier', 'private')}")
    log.info("=" * 60)

    # ── Launch Gateway ──
    gateway_config = config.get_section("gateway")
    host = gateway_config.get("host", "127.0.0.1")
    port = gateway_config.get("port", 8000)

    log.info("Starting API Gateway", host=host, port=port)

    uvicorn.run(
        "Backend.Gateway.App:app",
        host=host,
        port=port,
        reload=config.environment == "development",
        log_level="info",
        ws_ping_interval=20,
        ws_ping_timeout=20,
    )



if __name__ == "__main__":
    main()