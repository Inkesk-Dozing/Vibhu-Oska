"""
Vibhu-Oska AI-OS — Event Data Classes
Lightweight event wrappers used on the Python side of the event bus.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any


@dataclass
class Event:
    """
    A single event flowing through the ZeroMQ bus.

    This is the Python-side representation of the EventEnvelope protobuf.
    It serializes to JSON for transport over ZeroMQ.
    """

    topic: str
    source: str
    payload: dict[str, Any] = field(default_factory=dict)
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    destination: str = ""
    priority: int = 1  # 0=low, 1=normal, 2=high, 3=critical
    payload_type: str = ""

    # ==================================================================================================

    # # Internal Separation Division

    # =================─────────────────────────────────────────────────────────────────────────────────

    def serialize(self) -> str:
        """Serialize to JSON string for ZeroMQ transport."""
        return json.dumps(asdict(self), default=str)

    @classmethod
    def deserialize(cls, data: str) -> Event:
        """Deserialize from JSON string received via ZeroMQ."""
        parsed = json.loads(data)
        return cls(**parsed)

    def to_zmq_frames(self) -> list[bytes]:
        """
        Convert to ZeroMQ multi-part frames.
        Frame 0: topic (for PUB/SUB filtering)
        Frame 1: JSON payload
        """
        return [
            self.topic.encode("utf-8"),
            self.serialize().encode("utf-8"),
        ]

    @classmethod
    def from_zmq_frames(cls, frames: list[bytes]) -> Event:
        """Reconstruct from ZeroMQ multi-part frames."""
        # Frame 0 is the topic (already in the JSON), Frame 1 is the data
        data = frames[1].decode("utf-8")
        return cls.deserialize(data)


class EventFactory:
    """Factory methods for creating common event types."""

    @staticmethod
    def user_input(prompt: str, session_id: str = "", user_id: str = "operator", model_id: str = "") -> Event:
        return Event(
            topic="user.input",
            source="gateway",
            payload={
                "prompt": prompt,
                "session_id": session_id or str(uuid.uuid4()),
                "user_id": user_id,
                "model_id": model_id,
            },
            payload_type="TaskRequest",
        )

    @staticmethod
    def task_created(
        task_id: str,
        task_type: str,
        prompt: str,
        source: str = "orchestrator",
    ) -> Event:
        return Event(
            topic="task.created",
            source=source,
            payload={
                "task_id": task_id,
                "task_type": task_type,
                "prompt": prompt,
            },
            payload_type="TaskRequest",
        )

    @staticmethod
    def task_completed(
        task_id: str,
        content: str,
        source: str = "cognition",
    ) -> Event:
        return Event(
            topic="task.completed",
            source=source,
            payload={
                "task_id": task_id,
                "content": content,
            },
            payload_type="TaskResponse",
        )

    @staticmethod
    def task_failed(
        task_id: str,
        error: str,
        source: str = "cognition",
    ) -> Event:
        return Event(
            topic="task.failed",
            source=source,
            payload={
                "task_id": task_id,
                "error": error,
            },
            priority=2,
        )

    @staticmethod
    def tool_request(
        tool_name: str,
        action: str,
        arguments: dict[str, Any] | None = None,
        source: str = "cognition",
    ) -> Event:
        return Event(
            topic=f"tool.request.{tool_name}",
            source=source,
            payload={
                "tool_name": tool_name,
                "action": action,
                "arguments": arguments or {},
            },
            payload_type="ToolCall",
        )

    @staticmethod
    def tool_result(
        tool_name: str,
        action: str,
        result: Any,
        success: bool = True,
        source: str = "",
    ) -> Event:
        return Event(
            topic=f"tool.result.{tool_name}",
            source=source or tool_name,
            payload={
                "tool_name": tool_name,
                "action": action,
                "result": result,
                "success": success,
            },
            payload_type="ToolResult",
        )

    @staticmethod
    def heartbeat(source: str, uptime_seconds: int = 0, pending_tasks: int = 0) -> Event:
        return Event(
            topic="system.heartbeat",
            source=source,
            payload={
                "alive": True,
                "uptime_seconds": uptime_seconds,
                "pending_tasks": pending_tasks,
            },
            payload_type="Heartbeat",
        )

    @staticmethod
    def alert(
        source: str,
        title: str,
        description: str,
        severity: int = 1,
    ) -> Event:
        return Event(
            topic="system.alert",
            source=source,
            payload={
                "title": title,
                "description": description,
                "severity": severity,
            },
            priority=2 if severity >= 2 else 1,
            payload_type="Alert",
        )

    @staticmethod
    def health_check(health_data: dict[str, Any], source: str = "monitoring") -> Event:
        return Event(
            topic="system.health",
            source=source,
            payload=health_data,
            payload_type="SystemHealth",
        )
