"""
Vibhu-Oska AI-OS — ValidationCore
Performs double-validation checks (input safety + output schema compliance).
"""

from __future__ import annotations

import re
from typing import Any

from Backend.Plugins.ConfigLoader.ConfigLoader import ConfigLoader
from Shared.Models import TaskRequest, TaskResponse


class ValidationCore:
    """
    ValidationCore handles request safety inspection and schema enforcement.
    Ensures both user input and AI responses are verified before core routing.
    """

    def __init__(self) -> None:
        self._max_prompt_length = 100000
        self._block_patterns: list[str] = []
        self._initialized = False

    def initialize(self) -> None:
        """Load validation parameters from ConfigLoader."""
        if self._initialized:
            return

        config = ConfigLoader.load()
        validation_cfg = config.get_section("security.input_validation")
        self._max_prompt_length = validation_cfg.get("max_prompt_length", 100000)
        self._block_patterns = validation_cfg.get("block_patterns", [
            "DROP TABLE",
            "<script>",
            "rm -rf"
        ])
        self._initialized = True

    def validate_request(self, raw_data: Any) -> bool:
        """
        Orchestrator backward compatibility layer.
        Returns True if the request is structurally valid and safe.
        """
        valid, _ = self.validate_input_package(raw_data)
        return valid

    # ==================================================================================================

    # # Internal Separation Division

    # =================─────────────────────────────────────────────────────────────────────────────────

    def validate_input_package(self, raw_data: Any) -> tuple[bool, str]:
        """
        The 'Entry Gate'. Checks size, runs regex security block checks,
        and parses into a TaskRequest.

        Returns:
            (bool, reason_string)
        """
        if not self._initialized:
            self.initialize()

        # 1. Type check
        if not isinstance(raw_data, (dict, TaskRequest)):
            return False, "Input data must be a dictionary or a TaskRequest model."

        # 2. Extract prompt
        prompt = ""
        if isinstance(raw_data, dict):
            prompt = raw_data.get("prompt", "")
        else:
            prompt = raw_data.prompt

        # 3. Check length
        if len(prompt) > self._max_prompt_length:
            return False, f"Prompt exceeds maximum allowed length of {self._max_prompt_length} characters."

        # 4. Check block patterns (Security)
        for pattern in self._block_patterns:
            # Case insensitive check
            if re.search(re.escape(pattern), prompt, re.IGNORECASE):
                return False, f"Security violation: Blocked pattern '{pattern}' detected."

        # 5. Parse to Pydantic TaskRequest model
        if isinstance(raw_data, dict):
            try:
                # Pydantic validation handles standard structures
                TaskRequest(**raw_data)
            except Exception as e:
                return False, f"Schema validation error: {str(e)}"

        return True, "Valid"

    def validate_ai_output(self, ai_response: Any) -> tuple[bool, str]:
        """
        The 'Exit Gate'. Verifies the LLM response is safe, non-empty,
        and complies with the TaskResponse model contract.
        """
        if not self._initialized:
            self.initialize()

        # 1. Verify existence
        if not ai_response:
            return False, "AI response is empty."

        # 2. Check schema
        if isinstance(ai_response, dict):
            try:
                TaskResponse(**ai_response)
            except Exception as e:
                return False, f"AI Output schema mismatch: {str(e)}"
        elif not isinstance(ai_response, TaskResponse):
            return False, f"AI Output type mismatch. Expected TaskResponse, got: {type(ai_response).__name__}"

        # 3. Verify content length
        content = ai_response.content if hasattr(ai_response, "content") else ai_response.get("content", "")
        if not content or len(str(content).strip()) == 0:
            return False, "AI response contains empty content."

        return True, "Valid"