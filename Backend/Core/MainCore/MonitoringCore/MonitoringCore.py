"""
Vibhu-Oska AI-OS — MonitoringCore
Functional system telemetry, health checks, event auditing, and SQL logging.
"""

from __future__ import annotations

import json
import uuid
from typing import Any

from Backend.Plugins.ToolRegistry.Registry import ToolRegistry
from Backend.Core.EventBus.EventBus import EventBus
from Backend.Core.EventBus.Topics import Topics
from Backend.Core.EventBus.Events import Event


class MonitoringCore:
    """
    MonitoringCore handles system telemetry observation, reflection, and reporting.
    Listens to system-level event topics and logs metrics to SQLite telemetry tables.
    """

    def __init__(self) -> None:
        self._registry: ToolRegistry | None = None
        self._db: Any = None
        self._event_bus: EventBus | None = None
        self._initialized = False

    async def initialize(self, registry: ToolRegistry, event_bus: EventBus) -> None:
        """Initialize connections to tool registry, database, and event bus."""
        if self._initialized:
            return
        self._registry = registry
        self._db = registry.get("database_connector")
        self._event_bus = event_bus
        
        # Subscribe to system topics
        await self._event_bus.subscribe(Topics.SYSTEM_HEALTH, self.log_system_event)
        await self._event_bus.subscribe(Topics.SYSTEM_ALERT, self.log_system_event)
        self._initialized = True

    async def log_system_event(self, event: Event) -> None:
        """Log incoming system events directly into SQL telemetry logs."""
        if not self._db:
            return

        log_id = str(uuid.uuid4())
        source = event.source or "event_bus"
        level = "INFO"
        if event.topic == Topics.SYSTEM_ALERT:
            # Determine alert severity
            severity = event.payload.get("severity", 1)  # 1 = Warning, 2 = Error, 3 = Critical
            level = {1: "WARNING", 2: "ERROR", 3: "CRITICAL"}.get(severity, "INFO")
            
        message = event.payload.get("message", f"Event received: {event.topic}")
        details_json = json.dumps(event.payload)

        query = """
            INSERT INTO telemetry_logs (log_id, source, level, message, timestamp, details_json)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, ?)
        """
        await self._db.execute("execute", query=query, params=(log_id, source, level, message, details_json))

    # ==================================================================================================

    # # Internal Separation Division

    # =================─────────────────────────────────────────────────────────────────────────────────

    def observe(self, system_data: dict[str, Any]) -> str:
        """Analyze raw system health status and return structured observations."""
        cpu = system_data.get("cpu_percent", 0.0)
        ram = system_data.get("ram_used_gb", 0.0)
        gpu = system_data.get("gpu_vram_used_gb", 0.0)
        
        observations = f"System Resource Metrics: CPU {cpu}%, RAM {ram}GB, VRAM {gpu}GB."
        if cpu > 90.0:
            observations += " WARNING: High CPU utilization detected."
        if ram > 14.0:
            observations += " WARNING: Excessive RAM consumption."
        return observations
    
    def reflect(self, observations: str) -> str:
        """Cognitive reflection reasoning based on observations."""
        reflections = f"Cognitive Analysis: {observations}"
        if "WARNING" in observations:
            reflections += " System load is entering critical threshold. Recommend target routing to CPU-only fallback or query cache."
        else:
            reflections += " Core operations are nominal. Optimization profiles can run at peak targets."
        return reflections
    
    def evaluate(self, reflections: str) -> dict[str, Any]:
        """Performance and efficiency assessment based on reflections."""
        status = "HEALTHY"
        recommend_fallback = False
        
        if "critical threshold" in reflections.lower():
            status = "DEGRADED"
            recommend_fallback = True
            
        return {
            "status": status,
            "reflections": reflections,
            "recommend_fallback": recommend_fallback
        }

    def start_timer(self) -> float:
        """Utility function to measure operations speed."""
        import time
        return time.time()

    def log_event(self, reflections: str, execution_time: float) -> str:
        """Simple summary logging formatter."""
        return f"Reflections: {reflections} | Measured duration: {execution_time:.2f}s"
    
    async def generate_report(self) -> list[dict[str, Any]]:
        """Fetch and format the latest 20 telemetry records from the database."""
        if not self._db:
            return []
        query = "SELECT log_id, source, level, message, timestamp, details_json FROM telemetry_logs ORDER BY timestamp DESC LIMIT 20"
        return await self._db.execute("query", query=query)
    
    async def send_alert(self, reflections: str) -> str:
        """Publish system alert events to the bus and format string alert details."""
        evals = self.evaluate(reflections)
        alert_code = "SYS_ALERT_HIGH_LOAD" if evals["recommend_fallback"] else "SYS_NOMINAL"
        alert_type = "CRITICAL" if evals["recommend_fallback"] else "INFO"
        
        if self._event_bus and evals["recommend_fallback"]:
            # Fire an actual event alert
            from Backend.Core.EventBus.Events import EventFactory
            alert_event = EventFactory.alert(
                source="monitoring",
                title="System Resource Overload",
                description=reflections,
                severity=2  # Error
            )
            await self._event_bus.publish(alert_event)

        return f"Alert Code: {alert_code}\nAlert Type: {alert_type}\nAlert Details: {reflections}"
