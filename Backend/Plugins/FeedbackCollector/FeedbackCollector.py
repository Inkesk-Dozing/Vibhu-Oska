"""
Vibhu-Oska AI-OS — FeedbackCollector Plugin
RLHF-Lite: Captures operator approve/reject signals and exports them
as structured training data for the QLoRA fine-tuning pipeline.
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


class FeedbackCollector(BaseService):
    """
    Lightweight RLHF (Reinforcement Learning from Human Feedback) signal collector.

    Workflow:
      1. After each AI response, the frontend shows approve/reject buttons
      2. Signal is posted to /api/v1/events with topic 'feedback.signal'
      3. OrchestratorCore routes to FeedbackCollector.execute('log_feedback', ...)
      4. FeedbackCollector persists to SQLite + JSONL export file
      5. At training time, export_training_data() generates a JSONL dataset for QLoRA

    Training Data Format (output):
      {"prompt": "...", "response": "...", "reward": 1.0}  (approved)
      {"prompt": "...", "response": "...", "reward": -1.0} (rejected)
    """

    def __init__(self) -> None:
        self._db: Any = None
        self._export_path: Path | None = None
        self._initialized = False
        self._log = Logger.get("FeedbackCollector")

    # ══════════════════════════════════════════════════════════════
    # BaseService Interface
    # ══════════════════════════════════════════════════════════════

    def info(self) -> PluginInfo:
        return PluginInfo(
            name="feedback_collector",
            version="0.1.0",
            description="RLHF-Lite human feedback signal collector for model fine-tuning",
            capabilities=["log_feedback", "export_training_data", "get_stats"],
            status=CoreStatus.HEALTHY if self._initialized else CoreStatus.UNKNOWN,
            preferred_target=ExecutionTarget.CPU,
        )

    def health_check(self) -> bool:
        return self._initialized

    async def initialize(self) -> None:
        if self._initialized:
            return
        config = ConfigLoader.load()
        export_rel = config.get("plugins.feedback.export_path", "Data/training/feedback")
        self._export_path = config.project_root / export_rel
        self._export_path.mkdir(parents=True, exist_ok=True)

        # Create feedback table in SQLite via DatabaseConnector (lazy reference)
        self._initialized = True
        self._log.info("FeedbackCollector ready", export_path=str(self._export_path))

    async def shutdown(self) -> None:
        self._initialized = False

    async def execute(self, action: str, **kwargs: Any) -> Any:
        if action == "log_feedback":
            return await self.log_feedback(
                request_id=kwargs.get("request_id", ""),
                prompt=kwargs.get("prompt", ""),
                response=kwargs.get("response", ""),
                approved=bool(kwargs.get("approved", True)),
                annotation=kwargs.get("annotation", ""),
            )
        elif action == "export_training_data":
            return await self.export_training_data(
                output_file=kwargs.get("output_file", "feedback_dataset.jsonl")
            )
        elif action == "get_stats":
            return await self.get_stats()
        else:
            raise ValueError(f"Unknown FeedbackCollector action: {action}")

    # ══════════════════════════════════════════════════════════════
    # Feedback Logging
    # ══════════════════════════════════════════════════════════════

    async def log_feedback(
        self,
        request_id: str,
        prompt: str,
        response: str,
        approved: bool,
        annotation: str = "",
    ) -> dict[str, Any]:
        """
        Store a feedback signal. Each signal is:
        - Written to a JSONL file immediately (durable)
        - Optionally mirrored to SQLite via DatabaseConnector
        """
        entry = {
            "feedback_id": str(uuid.uuid4()),
            "request_id":  request_id,
            "timestamp":   datetime.now(timezone.utc).isoformat(),
            "approved":    approved,
            "reward":      1.0 if approved else -1.0,
            "prompt":      prompt,
            "response":    response[:1000] if response else "",
            "annotation":  annotation,
        }

        # Append to JSONL feedback log
        log_file = self._export_path / "feedback_log.jsonl"
        await asyncio.to_thread(self._append_jsonl, log_file, entry)

        self._log.info(
            "Feedback signal logged",
            request_id=request_id[:16],
            approved=approved,
            reward=entry["reward"],
        )
        return {"status": "logged", "feedback_id": entry["feedback_id"], "reward": entry["reward"]}

    def _append_jsonl(self, path: Path, entry: dict[str, Any]) -> None:
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    # ══════════════════════════════════════════════════════════════
    # Training Data Export
    # ══════════════════════════════════════════════════════════════

    async def export_training_data(self, output_file: str = "feedback_dataset.jsonl") -> dict[str, Any]:
        """
        Convert raw feedback log into QLoRA-ready training dataset.
        Output format: {"prompt": "...", "completion": "...", "reward": 1.0}
        Positive signals (approved) get reward=1.0, negative get reward=-1.0.
        Includes only entries with both prompt and response non-empty.
        """
        log_file = self._export_path / "feedback_log.jsonl"
        output   = self._export_path / output_file

        if not log_file.exists():
            return {"status": "no_data", "exported": 0}

        exported = 0
        skipped  = 0
        seen_prompts: set[str] = set()  # Dedup by prompt hash

        with open(log_file, "r", encoding="utf-8") as f_in, \
             open(output, "w", encoding="utf-8") as f_out:
            for line in f_in:
                try:
                    entry = json.loads(line.strip())
                except json.JSONDecodeError:
                    continue

                prompt   = entry.get("prompt", "").strip()
                response = entry.get("response", "").strip()
                reward   = float(entry.get("reward", 0.0))

                if not prompt or not response:
                    skipped += 1
                    continue

                # Deduplicate by prompt fingerprint
                key = prompt[:100]
                if key in seen_prompts and reward == 1.0:
                    skipped += 1
                    continue
                seen_prompts.add(key)

                training_example = {
                    "prompt":     f"<|system|>You are Vibhu-Oska AI-OS.<|end|><|user|>{prompt}<|end|><|assistant|>",
                    "completion": response,
                    "reward":     reward,
                }
                f_out.write(json.dumps(training_example, ensure_ascii=False) + "\n")
                exported += 1

        self._log.info("Training data exported", file=str(output), exported=exported, skipped=skipped)
        return {"status": "exported", "exported": exported, "skipped": skipped, "output_file": str(output)}

    # ══════════════════════════════════════════════════════════════
    # Stats
    # ══════════════════════════════════════════════════════════════

    async def get_stats(self) -> dict[str, Any]:
        """Return feedback statistics."""
        log_file = self._export_path / "feedback_log.jsonl"
        if not log_file.exists():
            return {"total": 0, "approved": 0, "rejected": 0, "approval_rate": 0.0}

        total = approved = rejected = 0
        with open(log_file, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    e = json.loads(line.strip())
                    total += 1
                    if e.get("approved"): approved += 1
                    else: rejected += 1
                except json.JSONDecodeError:
                    continue

        return {
            "total":         total,
            "approved":      approved,
            "rejected":      rejected,
            "approval_rate": round(approved / total, 3) if total else 0.0,
        }
