"""
Vibhu-Oska AI-OS — Base Service Interface
Abstract base class that all plugins/services must implement.

This is the unified contract that makes the Dynamic Tool Registry work.
Instead of 100+ hardcoded imports, every service inherits from BaseService
and registers itself with the ToolRegistry.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from Shared.Models import PluginInfo, CoreStatus, ExecutionTarget


class BaseService(ABC):
    """
    Abstract base class for all Vibhu-Oska plugins and services.

    Every plugin must implement:
        - info() → PluginInfo: Describe what this plugin is and does
        - execute() → Any: Perform the plugin's primary action
        - health_check() → bool: Report if the plugin is operational

    Lifecycle:
        1. Plugin is instantiated
        2. initialize() is called (optional async setup)
        3. Plugin is registered with the ToolRegistry
        4. execute() is called by OrchestratorCore when needed
        5. shutdown() is called during system teardown
    """

    # ══════════════════════════════════════════════════════════════════════
    # Required Implementations
    # ══════════════════════════════════════════════════════════════════════

    @abstractmethod
    def info(self) -> PluginInfo:
        """
        Return metadata about this plugin.
        Used by the registry for discovery and by the router for capability matching.
        """
        ...

    @abstractmethod
    async def execute(self, action: str, **kwargs: Any) -> Any:
        """
        Execute the plugin's primary functionality.

        Args:
            action: The specific action to perform (e.g., "search", "analyze", "format")
            **kwargs: Action-specific arguments

        Returns:
            The result of the action (type varies by plugin)

        Raises:
            ValueError: If the action is not supported
            RuntimeError: If the plugin is not in a healthy state
        """
        ...

    @abstractmethod
    def health_check(self) -> bool:
        """Return True if this plugin is operational and ready to receive tasks."""
        ...

    # ══════════════════════════════════════════════════════════════════════
    # Optional Lifecycle Hooks
    # ══════════════════════════════════════════════════════════════════════

    async def initialize(self) -> None:
        """
        Async initialization hook. Called after construction but before first use.
        Override this for async setup (database connections, model loading, etc.)
        """
        pass

    async def shutdown(self) -> None:
        """
        Graceful shutdown hook. Called during system teardown.
        Override this to clean up resources (close connections, flush buffers, etc.)
        """
        pass

    # ══════════════════════════════════════════════════════════════════════
    # Convenience Properties
    # ══════════════════════════════════════════════════════════════════════

    @property
    def name(self) -> str:
        """Plugin name derived from the info() method."""
        return self.info().name

    @property
    def version(self) -> str:
        """Plugin version derived from the info() method."""
        return self.info().version

    @property
    def capabilities(self) -> list[str]:
        """List of capabilities this plugin provides."""
        return self.info().capabilities

    def __repr__(self) -> str:
        info = self.info()
        return f"<{info.name} v{info.version} status={info.status.name}>"
