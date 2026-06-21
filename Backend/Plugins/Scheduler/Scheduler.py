"""
Vibhu-Oska AI-OS — Scheduler Plugin
Autonomous task scheduling: cron-like maintenance, model eval,
DB compaction, health checks — all self-managed by the AI-OS.
"""

from __future__ import annotations

import asyncio
import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from Backend.Plugins.ToolRegistry.BaseService import BaseService
from Backend.Plugins.Logger.Logger import Logger
from Backend.Plugins.ConfigLoader.ConfigLoader import ConfigLoader
from Shared.Models import PluginInfo, CoreStatus, ExecutionTarget


class ScheduledTask:
    """Represents a scheduled autonomous task."""
    __slots__ = ("task_id", "name", "cron", "topic", "payload", "enabled", "last_run", "run_count")

    def __init__(
        self,
        task_id: str,
        name: str,
        cron: str,
        topic: str,
        payload: dict[str, Any],
        enabled: bool = True,
    ) -> None:
        self.task_id   = task_id
        self.name      = name
        self.cron      = cron          # Simplified: "hourly" | "daily" | "weekly" | "*/N min"
        self.topic     = topic
        self.payload   = payload
        self.enabled   = enabled
        self.last_run: datetime | None = None
        self.run_count = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id":   self.task_id,
            "name":      self.name,
            "cron":      self.cron,
            "topic":     self.topic,
            "enabled":   self.enabled,
            "last_run":  self.last_run.isoformat() if self.last_run else None,
            "run_count": self.run_count,
        }


class Scheduler(BaseService):
    """
    Autonomous task scheduler for Vibhu-Oska AI-OS.

    Default schedules registered on boot:
      - Hourly: system health check
      - Nightly (3 AM): training data export from FeedbackCollector
      - Weekly: ChromaDB compaction

    Supports:
      - schedule(name, cron, topic, payload): Register new task
      - unschedule(task_id): Remove task
      - list_tasks(): All registered tasks
      - run_now(task_id): Force immediate execution
    """

    # Simplified cron intervals in seconds
    INTERVALS = {
        "hourly":      3600,
        "daily":       86400,
        "weekly":      604800,
        "*/5min":      300,
        "*/15min":     900,
        "*/30min":     1800,
    }

    def __init__(self) -> None:
        self._tasks:      dict[str, ScheduledTask] = {}
        self._event_bus:  Any = None
        self._runner:     asyncio.Task | None = None
        self._initialized = False
        self._log         = Logger.get("Scheduler")

    # ══════════════════════════════════════════════════════════════
    # BaseService Interface
    # ══════════════════════════════════════════════════════════════

    def info(self) -> PluginInfo:
        return PluginInfo(
            name="scheduler",
            version="0.1.0",
            description="Autonomous cron-like task scheduler for AI-OS maintenance",
            capabilities=["schedule", "unschedule", "list_tasks", "run_now"],
            status=CoreStatus.HEALTHY if self._initialized else CoreStatus.UNKNOWN,
            preferred_target=ExecutionTarget.CPU,
        )

    def health_check(self) -> bool:
        return self._initialized and (self._runner is not None and not self._runner.done())

    async def initialize(self) -> None:
        if self._initialized:
            return

        # Register default maintenance schedules
        self._register_defaults()

        # Start scheduler loop
        self._runner = asyncio.create_task(self._run_loop())
        self._initialized = True
        self._log.info("Scheduler started", tasks=len(self._tasks))

    def set_event_bus(self, event_bus: Any) -> None:
        """Inject event bus reference for task firing."""
        self._event_bus = event_bus

    async def shutdown(self) -> None:
        if self._runner:
            self._runner.cancel()
            try: await self._runner
            except asyncio.CancelledError: pass
        self._initialized = False

    async def execute(self, action: str, **kwargs: Any) -> Any:
        if action == "schedule":
            return self.schedule_task(
                name=kwargs["name"],
                cron=kwargs["cron"],
                topic=kwargs["topic"],
                payload=kwargs.get("payload", {}),
            )
        elif action == "unschedule":
            return self.unschedule(kwargs["task_id"])
        elif action == "list_tasks":
            return self.list_tasks()
        elif action == "run_now":
            return await self.run_now(kwargs["task_id"])
        else:
            raise ValueError(f"Unknown Scheduler action: {action}")

    # ══════════════════════════════════════════════════════════════
    # Default Schedules
    # ══════════════════════════════════════════════════════════════

    def _register_defaults(self) -> None:
        defaults = [
            {"name": "Health Check",          "cron": "hourly",  "topic": "system.health_check", "payload": {}},
            {"name": "Feedback Data Export",  "cron": "daily",   "topic": "feedback.export",     "payload": {"output_file": "nightly_feedback.jsonl"}},
            {"name": "Vector DB Compaction",  "cron": "weekly",  "topic": "memory.compact",      "payload": {}},
            {"name": "Model Eval Trigger",    "cron": "daily",   "topic": "training.eval",       "payload": {"model": "router"}},
            {"name": "Log Rotation",          "cron": "weekly",  "topic": "system.log_rotate",   "payload": {}},
        ]
        for d in defaults:
            self.schedule_task(d["name"], d["cron"], d["topic"], d["payload"])

    # ══════════════════════════════════════════════════════════════
    # Scheduling API
    # ══════════════════════════════════════════════════════════════

    def schedule_task(
        self,
        name: str,
        cron: str,
        topic: str,
        payload: dict[str, Any] | None = None,
        enabled: bool = True,
    ) -> dict[str, Any]:
        task_id = str(uuid.uuid4())
        task = ScheduledTask(
            task_id=task_id,
            name=name,
            cron=cron,
            topic=topic,
            payload=payload or {},
            enabled=enabled,
        )
        self._tasks[task_id] = task
        self._log.info("Task scheduled", name=name, cron=cron, topic=topic)
        return {"status": "scheduled", "task_id": task_id, "name": name}

    def unschedule(self, task_id: str) -> dict[str, Any]:
        if task_id in self._tasks:
            name = self._tasks[task_id].name
            del self._tasks[task_id]
            return {"status": "removed", "task_id": task_id, "name": name}
        return {"status": "not_found", "task_id": task_id}

    def list_tasks(self) -> list[dict[str, Any]]:
        return [t.to_dict() for t in self._tasks.values()]

    async def run_now(self, task_id: str) -> dict[str, Any]:
        task = self._tasks.get(task_id)
        if not task:
            return {"status": "not_found"}
        await self._fire_task(task)
        return {"status": "fired", "task_id": task_id, "name": task.name}

    # ══════════════════════════════════════════════════════════════
    # Scheduler Loop
    # ══════════════════════════════════════════════════════════════

    async def _run_loop(self) -> None:
        """Check every 60 seconds if any scheduled task is due."""
        while True:
            try:
                await asyncio.sleep(60)
                now = datetime.now(timezone.utc)
                for task in list(self._tasks.values()):
                    if not task.enabled:
                        continue
                    interval = self.INTERVALS.get(task.cron)
                    if interval is None:
                        continue  # Unknown cron string — skip
                    if task.last_run is None:
                        # Run 10 minutes after system start (not immediately on boot)
                        if (now - datetime.fromtimestamp(0, tz=timezone.utc)).total_seconds() > 600:
                            await self._fire_task(task)
                    else:
                        elapsed = (now - task.last_run).total_seconds()
                        if elapsed >= interval:
                            await self._fire_task(task)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self._log.error("Scheduler loop error", error=str(e))

    async def _fire_task(self, task: ScheduledTask) -> None:
        """Fire a scheduled task by publishing an event to the bus."""
        task.last_run = datetime.now(timezone.utc)
        task.run_count += 1
        self._log.info("Firing scheduled task", name=task.name, run=task.run_count)

        if self._event_bus:
            from Backend.Core.EventBus.Events import Event
            event = Event(
                topic=task.topic,
                source="scheduler",
                payload={**task.payload, "task_id": task.task_id, "task_name": task.name},
            )
            try:
                await self._event_bus.publish(event)
            except Exception as e:
                self._log.error("Failed to fire scheduled event", task=task.name, error=str(e))
