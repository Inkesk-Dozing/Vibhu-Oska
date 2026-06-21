"""
Vibhu-Oska AI-OS — Service Watchdog
Monitors plugin health and auto-restarts crashed services.
The immune system of the AI-OS.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

from Backend.Plugins.Logger.Logger import Logger
from Shared.Models import CoreStatus


class Watchdog:
    """
    Background service that monitors all registered plugins
    via their health_check() method.

    On failure detection:
      1. Attempts re-initialization (up to 3 times)
      2. If restart fails, marks plugin as DEGRADED
      3. Publishes SYSTEM_ALERT event to notify operator
      4. Logs to structured logger

    The Watchdog is NOT a BaseService (it's a core system component),
    so it doesn't go through the ToolRegistry. It's started directly
    by the API Gateway/Orchestrator during lifespan.
    """

    CHECK_INTERVAL = 30     # Seconds between health checks
    MAX_RESTARTS   = 3      # Max restart attempts before giving up

    def __init__(self, registry: Any, event_bus: Any) -> None:
        self._registry   = registry   # ToolRegistry reference
        self._event_bus  = event_bus  # EventBus reference
        self._task:      asyncio.Task | None = None
        self._running    = False
        self._restart_counts: dict[str, int] = {}
        self._log        = Logger.get("Watchdog")

    # ==================================================================================================

    # # Internal Separation Division

    # =================─────────────────────────────────────────────────────────────────────────────────

    async def start(self) -> None:
        """Start the watchdog background loop."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._watch_loop())
        self._log.info("Watchdog started", interval_s=self.CHECK_INTERVAL)

    async def stop(self) -> None:
        """Gracefully stop the watchdog."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self._task = None
        self._log.info("Watchdog stopped")

    async def _watch_loop(self) -> None:
        """Background loop executing health checks periodically."""
        while self._running:
            try:
                await asyncio.sleep(self.CHECK_INTERVAL)
                await self.check_services()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self._log.error("Error in watchdog health loop", error=str(e))

    async def check_services(self) -> None:
        """Retrieve all plugins and check health."""
        for info in self._registry.list_plugins():
            name = info.name
            service = self._registry.get_safe(name)
            if service is None:
                continue

            try:
                is_healthy = service.health_check()
            except Exception as e:
                self._log.error("Plugin health check raised exception", plugin=name, error=str(e))
                is_healthy = False

            if not is_healthy:
                self._log.warning("Unhealthy plugin detected by watchdog", plugin=name)
                await self._restart_service(name)

    async def _restart_service(self, name: str) -> None:
        """Attempt to recover/restart a failed service plugin."""
        count = self._restart_counts.get(name, 0)
        if count >= self.MAX_RESTARTS:
            self._log.error("Maximum restart limit reached. Service remains degraded.", plugin=name)
            return

        self._restart_counts[name] = count + 1
        self._log.warning("Attempting plugin restart", plugin=name, attempt=count + 1, max_attempts=self.MAX_RESTARTS)

        await self._publish_alert(
            f"Plugin Unhealthy: {name}",
            f"{name} is unhealthy. Attempting to restart (attempt {count + 1}/{self.MAX_RESTARTS}).",
            severity="warning"
        )

        service = self._registry.get_safe(name)
        if service is not None:
            try:
                # Call shutdown if defined
                if hasattr(service, "shutdown"):
                    try:
                        await service.shutdown()
                    except Exception:
                        pass
                
                await service.initialize()
                recheck = service.health_check()
                if recheck:
                    self._log.info("Plugin recovered after restart", plugin=name)
                    await self._publish_alert(
                        f"Plugin Recovered: {name}",
                        f"{name} was unhealthy and was successfully restarted.",
                        severity="info",
                    )
                    self._restart_counts.pop(name, None)
                    return
            except Exception as e:
                self._log.error("Plugin restart failed", plugin=name, error=str(e))

        await self._publish_alert(
            f"Plugin Restart Failed: {name}",
            f"Attempt {count + 1}/{self.MAX_RESTARTS} to restart {name} failed.",
            severity="warning",
        )

    async def _publish_alert(self, title: str, description: str, severity: str = "warning") -> None:
        """Publish a system alert event to the EventBus."""
        if not self._event_bus:
            return
        try:
            from Backend.Core.EventBus.Events import Event
            event = Event(
                topic="system.alert",
                source="watchdog",
                payload={
                    "title":       title,
                    "description": description,
                    "severity":    severity,
                    "timestamp":   datetime.now(timezone.utc).isoformat(),
                },
            )
            await self._event_bus.publish(event)
        except Exception as e:
            self._log.error("Watchdog failed to publish alert", error=str(e))