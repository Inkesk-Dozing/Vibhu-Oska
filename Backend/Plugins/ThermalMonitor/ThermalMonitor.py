"""
Vibhu-Oska AI-OS — ThermalMonitor Plugin
GPU + CPU temperature monitoring with automatic throttling.
Protects your RTX 4060 from sustained thermal stress.
"""

from __future__ import annotations

import asyncio
import subprocess
from typing import Any

from Backend.Plugins.ToolRegistry.BaseService import BaseService
from Backend.Plugins.Logger.Logger import Logger
from Shared.Models import PluginInfo, CoreStatus, ExecutionTarget


class ThermalReading:
    """Snapshot of system temperatures."""
    __slots__ = ("gpu_temp", "cpu_temp", "gpu_power_w", "gpu_util_pct", "cpu_util_pct", "ram_util_pct", "throttled")

    def __init__(
        self,
        gpu_temp: float = 0.0,
        cpu_temp: float = 0.0,
        gpu_power_w: float = 0.0,
        gpu_util_pct: float = 0.0,
        cpu_util_pct: float = 0.0,
        ram_util_pct: float = 0.0,
    ) -> None:
        self.gpu_temp     = gpu_temp
        self.cpu_temp     = cpu_temp
        self.gpu_power_w  = gpu_power_w
        self.gpu_util_pct = gpu_util_pct
        self.cpu_util_pct = cpu_util_pct
        self.ram_util_pct = ram_util_pct
        self.throttled    = gpu_temp > 83.0 or cpu_temp > 90.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "gpu_temp_c":   self.gpu_temp,
            "cpu_temp_c":   self.cpu_temp,
            "gpu_power_w":  self.gpu_power_w,
            "gpu_util_pct": self.gpu_util_pct,
            "cpu_util_pct": self.cpu_util_pct,
            "ram_util_pct": self.ram_util_pct,
            "throttled":    self.throttled,
        }


class ThermalMonitor(BaseService):
    """
    Temperature-aware scheduler for RTX 4060 + Ryzen 9.

    Monitors GPU temp via nvidia-smi and CPU via psutil.
    Publishes THERMAL_ALERT events when thresholds are exceeded.
    Auto-throttles GPU inference tasks when temp > 83°C.

    Actions:
      - read(): Current temperature snapshot
      - is_safe(): Returns True if safe to run GPU task
      - history(n): Last N readings
    """

    GPU_THROTTLE_TEMP = 83.0   # °C — throttle GPU tasks above this
    GPU_CRITICAL_TEMP = 90.0   # °C — stop GPU tasks entirely above this
    CPU_CRITICAL_TEMP = 90.0   # °C — CPU throttle threshold

    def __init__(self) -> None:
        self._history:     list[ThermalReading] = []
        self._max_history: int = 60            # Keep last 60 readings (= 10 min at 10s intervals)
        self._monitor_task: asyncio.Task | None = None
        self._event_bus:    Any = None
        self._initialized   = False
        self._has_nvidia    = False
        self._log           = Logger.get("ThermalMonitor")

    # ══════════════════════════════════════════════════════════════
    # BaseService Interface
    # ══════════════════════════════════════════════════════════════

    def info(self) -> PluginInfo:
        return PluginInfo(
            name="thermal_monitor",
            version="0.1.0",
            description="GPU/CPU temperature monitoring with auto-throttling for RTX 4060",
            capabilities=["read", "is_safe", "history"],
            status=CoreStatus.HEALTHY if self._initialized else CoreStatus.UNKNOWN,
            preferred_target=ExecutionTarget.CPU,
        )

    def health_check(self) -> bool:
        return self._initialized

    def set_event_bus(self, event_bus: Any) -> None:
        self._event_bus = event_bus

    async def initialize(self) -> None:
        if self._initialized:
            return

        # Check if nvidia-smi is available
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
                capture_output=True, text=True, timeout=5
            )
            self._has_nvidia = result.returncode == 0
            if self._has_nvidia:
                gpu_name = result.stdout.strip()
                self._log.info("NVIDIA GPU detected", gpu=gpu_name)
        except FileNotFoundError:
            self._has_nvidia = False
            self._log.warning("nvidia-smi not found — GPU temp monitoring disabled")

        # Start background monitoring loop
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        self._initialized = True
        self._log.info("ThermalMonitor started", has_nvidia=self._has_nvidia)

    async def shutdown(self) -> None:
        if self._monitor_task:
            self._monitor_task.cancel()
            try: await self._monitor_task
            except asyncio.CancelledError: pass
        self._initialized = False

    async def execute(self, action: str, **kwargs: Any) -> Any:
        if action == "read":
            return (await self.read()).to_dict()
        elif action == "is_safe":
            return await self.is_safe()
        elif action == "history":
            n = int(kwargs.get("n", 10))
            return [r.to_dict() for r in self._history[-n:]]
        else:
            raise ValueError(f"Unknown ThermalMonitor action: {action}")

    # ══════════════════════════════════════════════════════════════
    # Temperature Reading
    # ══════════════════════════════════════════════════════════════

    async def read(self) -> ThermalReading:
        """Read current GPU and CPU temperatures."""
        gpu_temp = gpu_power = gpu_util = 0.0
        cpu_temp = 0.0
        cpu_util = 0.0
        ram_util = 0.0

        try:
            import psutil
            cpu_util = psutil.cpu_percent()
            ram_util = psutil.virtual_memory().percent
        except Exception:
            pass

        if self._has_nvidia:
            try:
                result = await asyncio.to_thread(
                    subprocess.run,
                    ["nvidia-smi",
                     "--query-gpu=temperature.gpu,power.draw,utilization.gpu",
                     "--format=csv,noheader,nounits"],
                    capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0:
                    parts = [p.strip() for p in result.stdout.strip().split(",")]
                    if len(parts) >= 3:
                        gpu_temp  = float(parts[0]) if parts[0] != "[N/A]" else 0.0
                        gpu_power = float(parts[1]) if parts[1] != "[N/A]" else 0.0
                        gpu_util  = float(parts[2]) if parts[2] != "[N/A]" else 0.0
            except Exception as e:
                self._log.debug("nvidia-smi read error", error=str(e))

        # CPU temperature via psutil
        try:
            import psutil
            temps = psutil.sensors_temperatures()
            if temps:
                # Try common sensor names for different platforms
                for sensor_name in ("coretemp", "k10temp", "cpu_thermal", "acpitz"):
                    if sensor_name in temps:
                        readings = temps[sensor_name]
                        if readings:
                            cpu_temp = max(r.current for r in readings)
                        break
        except Exception:
            pass  # psutil may not have temp sensors on all platforms

        reading = ThermalReading(
            gpu_temp=gpu_temp,
            cpu_temp=cpu_temp,
            gpu_power_w=gpu_power,
            gpu_util_pct=gpu_util,
            cpu_util_pct=cpu_util,
            ram_util_pct=ram_util
        )
        return reading

    async def is_safe(self) -> dict[str, Any]:
        """Return whether it's safe to dispatch GPU inference tasks."""
        reading = await self.read()
        safe = reading.gpu_temp < self.GPU_THROTTLE_TEMP and reading.cpu_temp < self.CPU_CRITICAL_TEMP
        return {
            "safe":         safe,
            "gpu_temp_c":   reading.gpu_temp,
            "cpu_temp_c":   reading.cpu_temp,
            "throttle_at":  self.GPU_THROTTLE_TEMP,
            "reason":       None if safe else f"GPU {reading.gpu_temp}°C exceeds throttle threshold {self.GPU_THROTTLE_TEMP}°C",
        }

    # ══════════════════════════════════════════════════════════════
    # Background Monitoring Loop
    # ══════════════════════════════════════════════════════════════

    async def _monitor_loop(self) -> None:
        """Poll temperatures every 10 seconds and publish alerts if critical."""
        while True:
            try:
                await asyncio.sleep(10)
                reading = await self.read()

                # Store in history
                self._history.append(reading)
                if len(self._history) > self._max_history:
                    self._history.pop(0)

                # Publish thermal alerts
                if self._event_bus:
                    if reading.gpu_temp >= self.GPU_CRITICAL_TEMP:
                        await self._publish_alert("CRITICAL_GPU_TEMP", reading)
                    elif reading.gpu_temp >= self.GPU_THROTTLE_TEMP:
                        await self._publish_alert("HIGH_GPU_TEMP", reading)

            except asyncio.CancelledError:
                break
            except Exception as e:
                self._log.error("Thermal monitor loop error", error=str(e))

    async def _publish_alert(self, alert_type: str, reading: ThermalReading) -> None:
        """Publish a thermal alert event to the bus."""
        from Backend.Core.EventBus.Events import Event
        try:
            event = Event(
                topic="system.alert",
                source="thermal_monitor",
                payload={
                    "alert_type":  alert_type,
                    "title":       f"Thermal Alert: {alert_type.replace('_', ' ')}",
                    "description": f"GPU: {reading.gpu_temp}°C | CPU: {reading.cpu_temp}°C",
                    "severity":    "critical" if "CRITICAL" in alert_type else "warning",
                    **reading.to_dict(),
                },
            )
            await self._event_bus.publish(event)
        except Exception as e:
            self._log.error("Failed to publish thermal alert", error=str(e))
