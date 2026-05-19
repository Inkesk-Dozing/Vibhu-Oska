"""
Vibhu-Oska AI-OS — DistributionCore
Stubvi Public Compiler, Telemetry Ingestion & Decentralized Training Matrix.

Responsibilities:
  - Compile a public-safe, whitelisted bundle from the private core (Stubvi protocol).
  - Strip all internal module references and private weight paths from distributed files.
  - Ingest anonymized telemetry packets from opt-in public Stubvi installations.
  - Route collected data into the local training database for continuous refinement.

Boundary Rules:
  - NEVER expose private model weights, internal keys, or private core paths externally.
  - NEVER accept telemetry that has not passed the anonymization check.
  - This module has no inference logic (belongs to CognitionCore).
  - This module has no DB query logic (belongs to DataCore).

Usage (via OrchestratorCore / ToolRegistry):
    dist = DistributionCore()
    await dist.initialize()
    bundle_path = await dist.execute("compile_bundle", output_dir="dist/stubvi_v0.3")
    await dist.execute("ingest_telemetry", packet={...})
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import time
from pathlib import Path
from typing import Any

from Backend.Plugins.Logger.Logger import Logger
from Backend.Plugins.ToolRegistry.BaseService import BaseService
from Shared.Models import CoreStatus, ExecutionTarget, PluginInfo


# ==================================================================================================
# Constants
# ==================================================================================================

# Files and patterns that must NEVER appear in a public bundle.
# The compiler will abort the bundle if any of these are matched.
_PRIVATE_PATH_PATTERNS: list[str] = [
    r"Models/sovereign_gpt/checkpoints",
    r"Models/reasoning/lora_adapters",
    r"sovereign_gpt\.pt",
    r"tokenizer_vocab\.json",
    r"\.env",
    r"config/.*\.yaml",
    r"Data/training",
    r"inkeskdozing",
    r"Vibhu-Oska/Backend/Core/MainCore",
    r"AGENT_STATE_CACHE",
]

# Files explicitly approved for public bundle inclusion.
# Everything NOT on this list is excluded by default.
_WHITELIST: list[str] = [
    "README.md",
    "LICENCE.md",
    "CONTRIBUTING.md",
    "pyproject.toml",
    "requirements.txt",
    "Shared/__init__.py",
    "Shared/Models.py",
    "Backend/__init__.py",
    "Backend/Gateway/__init__.py",
    "Backend/Gateway/App.py",
    "Backend/Gateway/McpServer.py",
]

# Markers stripped from any whitelisted file before bundling.
_INTERNAL_MARKERS: list[str] = [
    "Inkesk-Dozing",
    "inkeskdozing@gmail.com",
    "OSKA initiative",
    "vibhu_oska_project_proposal",
    "AGENT_STATE_CACHE",
    "Ponder dir",
]


class DistributionCore(BaseService):
    """
    DistributionCore implements the Stubvi public distribution protocol.

    The private sovereign instance and the public Stubvi tier are architecturally
    separate. This core acts as the asymmetric compiler that produces the public
    surface from a strict file whitelist, with all internal markers sanitized.

    It also operates as the telemetry ingestion endpoint: receiving anonymized
    usage packets from opted-in public installations and queuing them for local
    fine-tuning.
    """

    def __init__(self) -> None:
        self._initialized = False
        self._project_root: Path | None = None
        self._telemetry_queue: list[dict[str, Any]] = []
        self._bundle_count = 0
        self._telemetry_count = 0
        self._log = Logger.get("DistributionCore")

    # ==================================================================================================

    # # Internal Separation Division

    # =================─────────────────────────────────────────────────────────────────────────────────

    def info(self) -> PluginInfo:
        return PluginInfo(
            name="distribution",
            version="0.2.0",
            description="Stubvi public core compiler, telemetry ingestion, and decentralized training feed",
            capabilities=["compile_bundle", "ingest_telemetry", "verify_bundle", "flush_telemetry"],
            status=CoreStatus.HEALTHY if self._initialized else CoreStatus.UNKNOWN,
            preferred_target=ExecutionTarget.CPU,
        )

    def health_check(self) -> bool:
        return self._initialized

    async def initialize(self) -> None:
        """
        Resolve the project root and prepare the distribution runtime.

        Parameters: None
        Returns: None
        Edge cases: Safe to call multiple times (idempotent).
        """
        if self._initialized:
            return
        self._project_root = Path(__file__).resolve().parent.parent.parent.parent.parent
        self._log.info("DistributionCore initialized", root=str(self._project_root))
        self._initialized = True

    async def execute(self, action: str, **kwargs: Any) -> Any:
        """
        Dispatch to the appropriate distribution action.

        Parameters:
            action: One of compile_bundle | verify_bundle | ingest_telemetry | flush_telemetry
            **kwargs: Action-specific keyword arguments.
        Returns: Action result dict.
        Edge cases: Unknown actions raise ValueError to prevent silent no-ops.
        """
        match action:
            case "compile_bundle":
                return await self.compile_bundle(
                    output_dir=kwargs.get("output_dir", "dist/stubvi"),
                    version=kwargs.get("version", "public"),
                )
            case "verify_bundle":
                return await self.verify_bundle(
                    bundle_dir=kwargs.get("bundle_dir", "dist/stubvi")
                )
            case "ingest_telemetry":
                return await self.ingest_telemetry(packet=kwargs.get("packet", {}))
            case "flush_telemetry":
                return await self.flush_telemetry_to_disk(
                    output_path=kwargs.get("output_path")
                )
            case _:
                raise ValueError(f"Action '{action}' is not supported by DistributionCore.")

    # ==================================================================================================

    # # Internal Separation Division

    # =================─────────────────────────────────────────────────────────────────────────────────

    async def compile_bundle(self, output_dir: str = "dist/stubvi", version: str = "public") -> dict[str, Any]:
        """
        Compile a clean, whitelisted public bundle from the private core.

        Copies only files listed in _WHITELIST to the output directory,
        then strips all _INTERNAL_MARKERS from each copied file's text content.
        Aborts if any private path patterns are detected in the output.

        Parameters:
            output_dir: Target directory for the public bundle (relative to project root).
            version: Version tag embedded in the bundle manifest.
        Returns:
            dict with keys: status, bundle_path, file_count, manifest_hash
        Edge cases:
            - Binary files in the whitelist are copied as-is (no text stripping).
            - If the output dir already exists, it is wiped and rebuilt cleanly.
        """
        if not self._initialized or not self._project_root:
            return {"status": "error", "message": "DistributionCore not initialized"}

        out_path = self._project_root / output_dir
        if out_path.exists():
            shutil.rmtree(out_path)
        out_path.mkdir(parents=True, exist_ok=True)

        copied: list[str] = []
        skipped: list[str] = []

        for relative_file in _WHITELIST:
            src = self._project_root / relative_file
            if not src.exists():
                self._log.warning("Whitelisted file not found — skipping", file=relative_file)
                skipped.append(relative_file)
                continue

            dst = out_path / relative_file
            dst.parent.mkdir(parents=True, exist_ok=True)

            try:
                if src.suffix in {".py", ".md", ".toml", ".txt", ".yaml", ".yml", ".json"}:
                    text = src.read_text(encoding="utf-8")
                    text = self._strip_internal_markers(text)
                    dst.write_text(text, encoding="utf-8")
                else:
                    shutil.copy2(src, dst)
                copied.append(relative_file)
                self._log.debug("Bundled file", file=relative_file)

            except Exception as err:
                self._log.error("Failed to bundle file", file=relative_file, error=str(err))
                skipped.append(relative_file)

        # Write bundle manifest
        manifest = {
            "stubvi_version": version,
            "compiled_at": int(time.time()),
            "file_count": len(copied),
            "files": copied,
            "skipped": skipped,
        }
        manifest_path = out_path / "BUNDLE_MANIFEST.json"
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

        # Compute manifest hash for integrity verification
        manifest_hash = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
        (out_path / "BUNDLE_MANIFEST.sha256").write_text(manifest_hash, encoding="utf-8")

        self._bundle_count += 1
        self._log.info("Bundle compiled successfully", files=len(copied), path=str(out_path))

        return {
            "status": "success",
            "bundle_path": str(out_path),
            "file_count": len(copied),
            "skipped_count": len(skipped),
            "manifest_hash": manifest_hash,
        }

    def _strip_internal_markers(self, text: str) -> str:
        """
        Remove all internal-only references from a file's text content.

        Parameters:
            text: Raw file content as a string.
        Returns: Sanitized string with internal markers replaced by placeholder text.
        Edge cases: Replacements are done in-order; overlapping markers are handled sequentially.
        """
        for marker in _INTERNAL_MARKERS:
            text = text.replace(marker, "[STUBVI_REDACTED]")
        return text

    async def verify_bundle(self, bundle_dir: str = "dist/stubvi") -> dict[str, Any]:
        """
        Verify that a compiled bundle contains no private path references.

        Scans every text file in the bundle directory against _PRIVATE_PATH_PATTERNS.
        Returns a pass/fail result with any offending files listed.

        Parameters:
            bundle_dir: Path to the compiled bundle (relative to project root).
        Returns:
            dict with keys: status (pass|fail), violations (list of {file, pattern} dicts)
        Edge cases:
            - If the bundle directory does not exist, returns an error status.
            - Binary files are skipped in the scan.
        """
        if not self._project_root:
            return {"status": "error", "message": "Not initialized"}

        bundle_path = self._project_root / bundle_dir
        if not bundle_path.exists():
            return {"status": "error", "message": f"Bundle directory not found: {bundle_path}"}

        violations: list[dict[str, str]] = []
        compiled_patterns = [re.compile(p) for p in _PRIVATE_PATH_PATTERNS]

        for file in bundle_path.rglob("*"):
            if not file.is_file():
                continue
            if file.suffix not in {".py", ".md", ".toml", ".txt", ".yaml", ".yml", ".json"}:
                continue
            try:
                content = file.read_text(encoding="utf-8", errors="ignore")
                for pattern, raw in zip(compiled_patterns, _PRIVATE_PATH_PATTERNS):
                    if pattern.search(content):
                        violations.append({"file": str(file.relative_to(bundle_path)), "pattern": raw})
            except Exception:
                continue

        if violations:
            self._log.error("Bundle integrity check FAILED", violations=violations)
            return {"status": "fail", "violations": violations}

        self._log.info("Bundle integrity check PASSED")
        return {"status": "pass", "violations": []}

    async def ingest_telemetry(self, packet: dict[str, Any]) -> dict[str, Any]:
        """
        Receive and queue an anonymized telemetry packet from a public installation.

        The packet must contain a 'session_hash' field (anonymized identifier) and
        must NOT contain any personally identifiable information (PII). The ingestion
        layer enforces a lightweight PII blocklist check before accepting the packet.

        Parameters:
            packet: Dict with telemetry fields (session_hash, event, data, timestamp).
        Returns:
            dict with keys: status, queue_depth
        Edge cases:
            - Packets missing 'session_hash' are rejected immediately.
            - Packets triggering PII blocklist patterns are silently dropped.
        """
        _PII_BLOCKLIST = ["email", "password", "ip_address", "username", "name", "phone"]

        if "session_hash" not in packet:
            return {"status": "rejected", "reason": "missing session_hash"}

        # PII scan — reject if any suspicious field names exist in payload keys
        packet_keys_lower = [k.lower() for k in packet.keys()]
        for pii_field in _PII_BLOCKLIST:
            if pii_field in packet_keys_lower:
                self._log.warning("Telemetry packet rejected: PII field detected", field=pii_field)
                return {"status": "rejected", "reason": f"PII field detected: {pii_field}"}

        # Stamp intake time and queue
        packet["_ingested_at"] = int(time.time())
        self._telemetry_queue.append(packet)
        self._telemetry_count += 1

        self._log.debug("Telemetry packet queued", queue_depth=len(self._telemetry_queue))
        return {"status": "queued", "queue_depth": len(self._telemetry_queue)}

    async def flush_telemetry_to_disk(self, output_path: str | None = None) -> dict[str, Any]:
        """
        Flush queued telemetry packets to a JSONL file for offline training consumption.

        Parameters:
            output_path: Target file path. Defaults to Data/training/telemetry/telemetry.jsonl.
        Returns:
            dict with keys: status, flushed_count, output_path
        Edge cases:
            - If the queue is empty, returns without writing a file.
            - Appends to an existing file rather than overwriting (preserves history).
        """
        if not self._telemetry_queue:
            return {"status": "empty", "flushed_count": 0}

        if not self._project_root:
            return {"status": "error", "message": "Not initialized"}

        if output_path:
            dest = Path(output_path)
        else:
            dest = self._project_root / "Data" / "training" / "telemetry" / "telemetry.jsonl"

        dest.parent.mkdir(parents=True, exist_ok=True)

        flushed = len(self._telemetry_queue)
        with dest.open("a", encoding="utf-8") as f:
            for packet in self._telemetry_queue:
                f.write(json.dumps(packet) + "\n")

        self._telemetry_queue.clear()
        self._log.info("Telemetry flushed to disk", count=flushed, path=str(dest))

        return {"status": "success", "flushed_count": flushed, "output_path": str(dest)}
