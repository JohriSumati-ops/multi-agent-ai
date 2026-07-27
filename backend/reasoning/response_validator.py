"""
reasoning/response_validator.py — THE RESPONSE VALIDATOR

WHY THIS FILE EXISTS
---------------------
See docs/Phase6.md Section 10. The last gate before an LLM's raw text
output is trusted as data — parses it as JSON, validates it against
`StructuredAnswer` (Pydantic does the schema/type/bounds checking), and
raises `LLMResponseError` with the raw text attached on any failure,
rather than attempting to silently repair malformed output. This project's
established rule against ever coercing bad data into a best guess (see
`core/exceptions.py`'s domain exception hierarchy from Phase 1) applies
here to model output exactly as it applies to a malformed API request.
"""

from __future__ import annotations

import json

from core.config import settings
from core.exceptions import LLMResponseError
from llm.prompts.templates import StructuredAnswer


class ResponseValidator:
    def validate(self, raw_text: str) -> StructuredAnswer:
        """
        Parses and validates `raw_text` (the model's raw completion)
        against `StructuredAnswer`. Strips a leading/trailing markdown
        code fence if present — models frequently wrap JSON in ```json
        blocks despite being instructed not to — but does NOT attempt any
        deeper repair beyond that one, extremely common, cosmetic case.
        """
        cleaned = self._strip_code_fence(raw_text)

        try:
            payload = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise LLMResponseError(
                "Model response was not valid JSON", details={"raw_response": raw_text}
            ) from exc

        try:
            answer = StructuredAnswer.model_validate(payload)
        except Exception as exc:  # noqa: BLE001 — pydantic.ValidationError, wrapped uniformly
            raise LLMResponseError(
                f"Model response did not match the required schema: {exc}",
                details={"raw_response": raw_text},
            ) from exc

        if answer.confidence < settings.LLM_MIN_CONFIDENCE:
            raise LLMResponseError(
                f"Model response confidence {answer.confidence} is below the minimum "
                f"threshold {settings.LLM_MIN_CONFIDENCE}",
                details={"raw_response": raw_text},
            )

        return answer

    @staticmethod
    def _strip_code_fence(text: str) -> str:
        stripped = text.strip()
        if stripped.startswith("```"):
            lines = stripped.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            stripped = "\n".join(lines)
        return stripped.strip()
