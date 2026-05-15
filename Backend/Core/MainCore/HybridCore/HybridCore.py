"""
Vibhu-Oska AI-OS — HybridCore (Execution Target Routing)
Monitors model endpoint health and routes requests to the primary engine or backup fallback.
"""

from __future__ import annotations

from typing import Any

from Backend.Core.BackupCore.BackupCore import BackupCore
from Backend.Core.MainCore.CognitionCore.cognition import CognitionCore
from Backend.Plugins.Logger.Logger import Logger
from Shared.Models import TaskResponse, ExecutionTarget, CoreStatus, StatusCode


class HybridCore:
    """
    HybridCore monitors primary intelligence health and routes tasks.
    Main Core (Sovereign GPT/GPU) ↔ Backup Core (Rules/CPU).
    """

    def __init__(self, primary_cognition: CognitionCore | None = None, backup_core: BackupCore | None = None) -> None:
        self._primary = primary_cognition or CognitionCore()
        self._backup = backup_core or BackupCore()
        self._status = CoreStatus.HEALTHY
        self._log = Logger.get("HybridCore")

    async def initialize(self) -> None:
        """Initialize both cognition cores."""
        await self._primary.initialize()
        self._status = CoreStatus.HEALTHY

    @property
    def status(self) -> CoreStatus:
        return self._status

    @property
    def backup_core(self) -> BackupCore:
        return self._backup

    async def check_health(self) -> bool:
        """Directly query primary model status to see if it is online."""
        try:
            # We can issue a test generate with a small max token limit to see if primary model responds
            test_resp = await self._primary.generate("ping", max_tokens=1)
            self._status = CoreStatus.HEALTHY
            return True
        except Exception:
            self._status = CoreStatus.DEGRADED
            return False

    # ==================================================================================================

    # # Internal Separation Division

    # =================─────────────────────────────────────────────────────────────────────────────────

    def _load_router(self) -> None:
        """Lazily load the router model and BPE tokenizer."""
        if hasattr(self, "_router") and self._router is not None:
            return

        try:
            import torch
            from pathlib import Path
            from Models.router.architecture import RouterConfig, VibhuOskaRouter
            from Models.sovereign_gpt.tokenizer import SovereignBPETokenizer

            root = Path(__file__).resolve().parent.parent.parent.parent.parent
            ckpt_dir = root / "Models" / "router" / "checkpoints"
            ckpt_path = ckpt_dir / "best_router.pt"
            vocab_path = ckpt_dir / "router_vocab.json"

            if not ckpt_path.exists() or not vocab_path.exists():
                self._log.warning("Router checkpoints not found. Speculative routing is disabled.", ckpt=str(ckpt_path))
                self._router = None
                self._router_tokenizer = None
                return

            self._log.info("Loading speculative router model and tokenizer...")
            self._router_tokenizer = SovereignBPETokenizer.load(vocab_path)

            checkpoint = torch.load(ckpt_path, map_location="cpu")
            cfg_dict = checkpoint["config"]

            valid_keys = {
                "vocab_size", "hidden_size", "intermediate_size", "num_layers",
                "num_heads", "max_seq_len", "dropout", "layer_norm_eps",
                "num_target_classes", "num_task_classes", "pad_token_id"
            }
            cfg_filtered = {k: v for k, v in cfg_dict.items() if k in valid_keys}

            config = RouterConfig(**cfg_filtered)
            model = VibhuOskaRouter(config)
            model.load_state_dict(checkpoint["model_state"])
            model.eval()

            self._router = model
            self._log.info("Router loaded successfully.")
        except Exception as e:
            self._log.error("Failed to load speculative router", error=str(e))
            self._router = None
            self._router_tokenizer = None

    async def process_request(
        self,
        prompt: str,
        system_prompt: str = "",
        context: list[dict[str, Any]] | None = None,
        model_id: str = ""
    ) -> TaskResponse:
        """
        Routes the request to primary local LLM first.
        Gracefully falls back to backup rules/CPU core if offline.
        """
        # Speculative routing if model_id is not explicitly set
        if not model_id:
            try:
                self._load_router()
                if hasattr(self, "_router") and self._router is not None and self._router_tokenizer is not None:
                    import torch
                    from Models.router.train import pad_sequence

                    raw_ids = self._router_tokenizer.encode(prompt)
                    max_len = self._router.config.max_seq_len
                    ids, attn = pad_sequence(raw_ids, max_len, pad_id=self._router_tokenizer.pad_id)

                    input_ids = torch.tensor([ids], dtype=torch.long)
                    attention_mask = torch.tensor([attn], dtype=torch.long)

                    prediction = self._router.predict(input_ids, attention_mask)
                    self._log.info(
                        "Speculative router predicted task/target",
                        task=prediction["task"],
                        target=prediction["target"],
                        task_conf=prediction["task_conf"],
                        target_conf=prediction["target_conf"]
                    )

                    if prediction["task"] == "CODE":
                        model_id = "vibhu-core"
                        self._log.info("Speculative routing matched CODE: routing to vibhu-core (Qwen 0.5B)")
                    elif prediction["task"] == "CHAT":
                        model_id = "sovereign-gpt"
                        self._log.info("Speculative routing matched CHAT: routing to sovereign-gpt")
                    else:
                        model_id = "sovereign-gpt"
            except Exception as e:
                self._log.warning("Speculative routing failed, defaulting to Sovereign GPT", error=str(e))
                model_id = "sovereign-gpt"

        # If backup core is explicitly requested
        if model_id == "backup-1":
            self._log.info("Explicitly routing request to Backup CPU Core", prompt_len=len(prompt))
            response = await self._backup.generate(prompt, system_prompt=system_prompt)
            response.metadata.executed_on = ExecutionTarget.CPU
            return response

        # Try primary
        try:
            self._log.info("Routing request to primary local GPU inference engine", prompt_len=len(prompt))
            response = await self._primary.generate(prompt, system_prompt=system_prompt, context=context, model_id=model_id)

            # Update target metadata
            response.metadata.executed_on = ExecutionTarget.GPU
            self._status = CoreStatus.HEALTHY
            return response

        except Exception as e:
            self._log.warning(
                "Primary GPU inference offline or failed. Gracefully falling back to Backup CPU Core.",
                error=str(e)
            )
            self._status = CoreStatus.DEGRADED

            # Try backup core
            response = await self._backup.generate(prompt, system_prompt=system_prompt)
            response.metadata.executed_on = ExecutionTarget.CPU

            # Mark degraded status
            if response.metadata.status.code == StatusCode.COMPLETED:
                response.metadata.status.message = "Served via backup CPU fallback: " + response.metadata.status.message

            return response
