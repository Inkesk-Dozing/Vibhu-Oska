"""
Vibhu-Oska AI-OS — ReplayLogger Plugin
Records all agent actions as replayable JSONL logs.
Critical for debugging autonomous behavior and demonstrating capability.
"""

from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from Backend.Plugins.ToolRegistry.BaseService import BaseService
from Backend.Plugins.Logger.Logger import Logger
from Backend.Plugins.ConfigLoader.ConfigLoader import ConfigLoader
from Shared.Models import PluginInfo, CoreStatus, ExecutionTarget


class ReplayLogger(BaseService):
    """
    Execution replay recording system.

    Every significant agent action (tool calls, code generation, test runs,
    feedback signals, routing decisions) is recorded as a timestamped JSONL entry.

    Replay entries can be played back for debugging, auditing, or training data creation.

    Actions:
      - record(action_type, details, session_id): Append entry to log
      - replay(session_id): Return all actions for a session in order
      - list_sessions(): List all session IDs with action counts
      - export_session(session_id, output_file): Export session as JSON
    """

    def __init__(self) -> None:
        self._log_dir: Path | None = None
        self._initialized = False
        self._log = Logger.get("ReplayLogger")

    # ══════════════════════════════════════════════════════════════
    # BaseService Interface
    # ══════════════════════════════════════════════════════════════

    def info(self) -> PluginInfo:
        return PluginInfo(
            name="replay_logger",
            version="0.1.0",
            description="Execution replay recording — records all agent actions as replayable logs",
            capabilities=["record", "replay", "list_sessions", "export_session"],
            status=CoreStatus.HEALTHY if self._initialized else CoreStatus.UNKNOWN,
            preferred_target=ExecutionTarget.CPU,
        )

    def health_check(self) -> bool:
        return self._initialized

    async def initialize(self) -> None:
        if self._initialized:
            return
        config = ConfigLoader.load()
        log_rel = config.get("plugins.replay.log_dir", "Log/replay")
        self._log_dir = config.project_root / log_rel
        self._log_dir.mkdir(parents=True, exist_ok=True)
        self._initialized = True
        self._log.info("ReplayLogger ready", log_dir=str(self._log_dir))

    async def shutdown(self) -> None:
        self._initialized = False

    async def execute(self, action: str, **kwargs: Any) -> Any:
        if action == "record":
            return await self.record(
                action_type=kwargs["action_type"],
                details=kwargs.get("details", {}),
                session_id=kwargs.get("session_id", "global"),
            )
        elif action == "replay":
            return await self.replay(kwargs["session_id"])
        elif action == "list_sessions":
            return await self.list_sessions()
        elif action == "export_session":
            return await self.export_session(
                session_id=kwargs["session_id"],
                output_file=kwargs.get("output_file", ""),
            )
        else:
            raise ValueError(f"Unknown ReplayLogger action: {action}")

    # ══════════════════════════════════════════════════════════════
    # Record
    # ══════════════════════════════════════════════════════════════

    async def record(
        self,
        action_type: str,
        details: dict[str, Any] | str,
        session_id: str = "global",
    ) -> dict[str, Any]:
        """Append an action entry to the session log."""
        entry = {
            "entry_id":    str(uuid.uuid4()),
            "timestamp":   datetime.now(timezone.utc).isoformat(),
            "action_type": action_type,
            "session_id":  session_id,
            "details":     details if isinstance(details, dict) else {"message": str(details)},
        }

        log_file = self._log_dir / f"session_{self._safe_name(session_id)}.jsonl"
        await asyncio.to_thread(self._append, log_file, entry)
        return {"status": "recorded", "entry_id": entry["entry_id"]}

    def _append(self, path: Path, entry: dict[str, Any]) -> None:
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")

    # ══════════════════════════════════════════════════════════════
    # Replay
    # ══════════════════════════════════════════════════════════════

    async def replay(self, session_id: str) -> list[dict[str, Any]]:
        """Return all recorded actions for a session in chronological order."""
        log_file = self._log_dir / f"session_{self._safe_name(session_id)}.jsonl"
        if not log_file.exists():
            return []

        entries = []
        with open(log_file, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    entries.append(json.loads(line.strip()))
                except json.JSONDecodeError:
                    continue

        return sorted(entries, key=lambda e: e.get("timestamp", ""))

    # ══════════════════════════════════════════════════════════════
    # List Sessions
    # ══════════════════════════════════════════════════════════════

    async def list_sessions(self) -> list[dict[str, Any]]:
        """List all recorded sessions with metadata."""
        sessions = []
        for log_file in sorted(self._log_dir.glob("session_*.jsonl")):
            count = 0
            first_ts = last_ts = ""
            with open(log_file, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        e = json.loads(line.strip())
                        count += 1
                        ts = e.get("timestamp", "")
                        if not first_ts: first_ts = ts
                        last_ts = ts
                    except json.JSONDecodeError:
                        continue
            sessions.append({
                "session_id":    log_file.stem.replace("session_", ""),
                "action_count":  count,
                "first_action":  first_ts,
                "last_action":   last_ts,
                "file_size_kb":  round(log_file.stat().st_size / 1024, 1),
            })
        return sessions

    # ══════════════════════════════════════════════════════════════
    # Export
    # ══════════════════════════════════════════════════════════════

    async def export_session(self, session_id: str, output_file: str = "") -> dict[str, Any]:
        """Export a session to a structured JSON file."""
        entries = await self.replay(session_id)
        if not entries:
            return {"status": "no_data", "session_id": session_id}

        out_path = self._log_dir / (output_file or f"export_{self._safe_name(session_id)}.json")
        out_path.write_text(json.dumps({"session_id": session_id, "actions": entries}, indent=2, default=str), encoding="utf-8")

        return {"status": "exported", "file": str(out_path), "action_count": len(entries)}

    def _safe_name(self, name: str) -> str:
        """Make a string safe for use as a filename."""
        return re.sub(r"[^\w\-]", "_", name)[:64]


import re  # noqa: E402 — needed by _safe_name
