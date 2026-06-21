"""
Vibhu-Oska AI-OS — Dynamic Tool Registry
Central registry that manages all plugin services.

Replaces the 100+ hardcoded Utils imports with a dynamic,
discoverable plugin system. OrchestratorCore and CognitionCore
reference tools by name, and the registry handles instantiation,
lifecycle, and routing.

Architecture:
    OrchestratorCore ──► ToolRegistry.get("search_engine") ──► SearchEngine.execute(...)
    CognitionCore    ──► JSON tool-call ──► OrchestratorCore ──► ToolRegistry ──► Plugin
"""

from __future__ import annotations

from typing import Any

from Backend.Plugins.ToolRegistry.BaseService import BaseService
from Shared.Models import PluginInfo, CoreStatus


class ToolRegistry:
    """
    Dynamic plugin registry for the Vibhu-Oska AI-OS.

    Usage:
        registry = ToolRegistry()

        # Register a plugin
        registry.register(MySearchEngine())
        registry.register(MyCodeAnalyzer())

        # Get and use a plugin
        search = registry.get("search_engine")
        results = await search.execute("search", query="ZeroMQ patterns")

        # List all plugins
        for info in registry.list_plugins():
            print(f"{info.name} v{info.version}: {info.capabilities}")
    """

    def __init__(self) -> None:
        self._plugins: dict[str, BaseService] = {}
        self._initialized: set[str] = set()

    # ══════════════════════════════════════════════════════════════════════
    # Registration
    # ══════════════════════════════════════════════════════════════════════

    def register(self, plugin: BaseService) -> None:
        """
        Register a plugin with the registry.

        Args:
            plugin: An instance of a class implementing BaseService

        Raises:
            TypeError: If the plugin doesn't extend BaseService
            ValueError: If a plugin with the same name is already registered
        """
        if not isinstance(plugin, BaseService):
            raise TypeError(
                f"Plugin must extend BaseService. Got: {type(plugin).__name__}"
            )

        info = plugin.info()
        name = info.name

        if name in self._plugins:
            raise ValueError(
                f"Plugin '{name}' is already registered. "
                f"Use unregister('{name}') first to replace it."
            )

        self._plugins[name] = plugin

    async def register_and_init(self, plugin: BaseService) -> None:
        """Register a plugin and call its async initialize() method."""
        self.register(plugin)
        name = plugin.info().name
        await plugin.initialize()
        self._initialized.add(name)

    def unregister(self, name: str) -> BaseService | None:
        """
        Remove a plugin from the registry.

        Returns:
            The removed plugin instance, or None if not found
        """
        plugin = self._plugins.pop(name, None)
        self._initialized.discard(name)
        return plugin

    # ══════════════════════════════════════════════════════════════════════
    # Access
    # ══════════════════════════════════════════════════════════════════════

    def get(self, name: str) -> BaseService:
        """
        Retrieve a registered plugin by name.

        Args:
            name: The plugin name (as returned by plugin.info().name)

        Raises:
            KeyError: If no plugin with that name is registered
        """
        if name not in self._plugins:
            available = ", ".join(self._plugins.keys()) or "(none)"
            raise KeyError(
                f"Plugin '{name}' is not registered. Available: {available}"
            )
        return self._plugins[name]

    def get_safe(self, name: str) -> BaseService | None:
        """Retrieve a plugin or return None if not found."""
        return self._plugins.get(name)

    def has(self, name: str) -> bool:
        """Check if a plugin is registered."""
        return name in self._plugins

    # ══════════════════════════════════════════════════════════════════════
    # Discovery
    # ══════════════════════════════════════════════════════════════════════

    def list_plugins(self) -> list[PluginInfo]:
        """Return metadata for all registered plugins."""
        infos = []
        for plugin in self._plugins.values():
            info = plugin.info()
            # Update status based on health check
            try:
                info.status = CoreStatus.HEALTHY if plugin.health_check() else CoreStatus.DEGRADED
            except Exception:
                info.status = CoreStatus.OFFLINE
            infos.append(info)
        return infos

    def find_by_capability(self, capability: str) -> list[BaseService]:
        """
        Find all plugins that advertise a given capability.

        Args:
            capability: The capability to search for (e.g., "web_search", "code_analysis")

        Returns:
            List of plugins that have this capability
        """
        return [
            plugin for plugin in self._plugins.values()
            if capability in plugin.info().capabilities
        ]

    @property
    def plugin_count(self) -> int:
        """Total number of registered plugins."""
        return len(self._plugins)

    @property
    def plugin_names(self) -> list[str]:
        """Names of all registered plugins."""
        return list(self._plugins.keys())

    # ══════════════════════════════════════════════════════════════════════
    # Lifecycle Management
    # ══════════════════════════════════════════════════════════════════════

    async def initialize_all(self) -> dict[str, bool]:
        """
        Initialize all registered plugins.

        Returns:
            Dict mapping plugin names to initialization success/failure
        """
        results: dict[str, bool] = {}
        for name, plugin in self._plugins.items():
            if name in self._initialized:
                results[name] = True
                continue
            try:
                await plugin.initialize()
                self._initialized.add(name)
                results[name] = True
            except Exception:
                results[name] = False
        return results

    async def shutdown_all(self) -> None:
        """Gracefully shut down all registered plugins."""
        for name, plugin in self._plugins.items():
            try:
                await plugin.shutdown()
            except Exception:
                pass  # Best-effort shutdown
        self._initialized.clear()

    # ══════════════════════════════════════════════════════════════════════
    # Health
    # ══════════════════════════════════════════════════════════════════════

    def health_report(self) -> dict[str, dict[str, Any]]:
        """
        Generate a health report for all registered plugins.

        Returns:
            Dict mapping plugin names to their health status and info
        """
        report: dict[str, dict[str, Any]] = {}
        for name, plugin in self._plugins.items():
            try:
                healthy = plugin.health_check()
                report[name] = {
                    "healthy": healthy,
                    "initialized": name in self._initialized,
                    "version": plugin.info().version,
                    "capabilities": plugin.info().capabilities,
                }
            except Exception as e:
                report[name] = {
                    "healthy": False,
                    "error": str(e),
                }
        return report

    def __repr__(self) -> str:
        return f"<ToolRegistry plugins={self.plugin_count} initialized={len(self._initialized)}>"
