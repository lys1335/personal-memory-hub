"""ReflectionProvider — LLM provider abstraction for ReflectionEngine.

Per D4.2d §2.7: "LLM invocation — Service manages AI provider communication"
ReflectionEngine must NOT depend on concrete LLM implementations.

This module provides:
- ReflectionProvider protocol (abstract interface)
- OllamaReflectionProvider (MVP implementation)
- MockReflectionProvider (for testing)

Future: OpenAIReflectionProvider, LocalReflectionProvider, etc.
"""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from typing import Any

logger = logging.getLogger(__name__)


class ReflectionProvider(ABC):
    """Abstract interface for LLM-based reflection inference.

    All Engines that need LLM reasoning MUST go through this interface.
    Concrete implementations (Ollama, OpenAI, etc.) live in shared/providers/.
    """

    @abstractmethod
    async def generate(self, prompt: str, context: dict[str, Any]) -> dict[str, Any]:
        """Generate structured output from LLM.

        Args:
            prompt: System/user prompt for the LLM.
            context: Additional context (e.g., candidate memories, scope).

        Returns:
            Parsed JSON dict with structured output.
        """
        ...


class OllamaReflectionProvider(ReflectionProvider):
    """Ollama-based ReflectionProvider using a custom Modelfile.

    MVP implementation. Configuration via environment variables:
    - REFLECTION_MODEL (default: "reflection-engine")
    - REFLECTION_TEMPERATURE (default: 0.3)
    - OLLAMA_BASE_URL (default: "http://localhost:11434")
    """

    def __init__(
        self,
        model: str | None = None,
        temperature: float | None = None,
        base_url: str | None = None,
    ) -> None:
        import os

        self.model = model or os.environ.get("REFLECTION_MODEL", "reflection-engine")
        self.temperature = (
            temperature
            if temperature is not None
            else float(os.environ.get("REFLECTION_TEMPERATURE", "0.3"))
        )
        self.base_url = (
            base_url or os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
        )
        self._log = logging.getLogger(f"{__name__}.Ollama")

    async def generate(
        self, prompt: str, context: dict[str, Any]
    ) -> dict[str, Any]:
        """Call Ollama API with structured prompt."""

        try:
            import httpx
        except ImportError:
            # Fallback to urllib if httpx not available
            return await self._generate_with_urllib(prompt, context)

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": self.temperature},
        }

        url = f"{self.base_url}/api/generate"
        self._log.info("Calling Ollama: model=%s, url=%s", self.model, url)

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            raw = resp.json()

        # Ollama generate returns "response" field
        text_response = raw.get("response", "")
        return self._parse_json_output(text_response)

    async def _generate_with_urllib(
        self, prompt: str, context: dict[str, Any]
    ) -> dict[str, Any]:
        """Fallback using urllib for environments without httpx."""
        import urllib.error
        import urllib.request

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": self.temperature},
        }

        data = json.dumps(payload).encode("utf-8")
        url = f"{self.base_url}/api/generate"

        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        self._log.info("Calling Ollama (urllib): model=%s, url=%s", self.model, url)

        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                raw = json.loads(resp.read().decode("utf-8"))
        except urllib.error.URLError as e:
            self._log.error("Ollama connection failed: %s", e)
            raise

        text_response = raw.get("response", "")
        return self._parse_json_output(text_response)

    @staticmethod
    def _parse_json_output(text: str) -> dict[str, Any]:
        """Parse LLM text response into structured JSON.

        Handles cases where LLM wraps JSON in markdown code blocks
        like ```json { ... } ``` or just ``` { ... } ```.
        """
        text = text.strip()

        # Strip markdown code fences if present (with or without language)
        if text.startswith("```"):
            lines = text.split("\n")
            # Remove opening fence (possibly with language tag like ```json)
            if lines:
                lines = lines[1:]
            # Remove closing fence
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines).strip()

        # If still starts with {, try to parse
        if text.startswith("{"):
            try:
                result = json.loads(text)
                if isinstance(result, dict):
                    return result
                else:
                    logger.warning("LLM output is not a dict: %s", text[:200])
                    return {"error": "invalid_json", "raw": text}
            except json.JSONDecodeError as e:
                logger.warning("Failed to parse LLM output as JSON: %s - Error: %s", text[:200], e)
                return {"error": "invalid_json", "raw": text, "parsed_error": str(e)}

        # Try to find JSON in the text
        import re
        json_match = re.search(r'\{[^{}]*"facts"[^{}]*\}', text, re.DOTALL)
        if json_match:
            try:
                result = json.loads(json_match.group())
                if isinstance(result, dict):
                    return result
            except json.JSONDecodeError:
                pass

        logger.warning("Failed to parse LLM output as JSON: %s", text[:200])
        return {"error": "invalid_json", "raw": text}


class MockReflectionProvider(ReflectionProvider):
    """Mock provider for unit testing.

    Returns deterministic results based on input, useful for Engine tests.
    """

    def __init__(self, mock_data: dict[str, Any] | None = None) -> None:
        self._mock_data = mock_data or {}
        self.call_count: int = 0
        self.last_prompt: str | None = None

    async def generate(
        self, prompt: str, context: dict[str, Any]
    ) -> dict[str, Any]:
        self.call_count += 1
        self.last_prompt = prompt

        if self._mock_data:
            return self._mock_data

        # Default mock response
        return {
            "facts": [],
            "entities": [],
            "interest_trends": {},
            "proposals": [],
        }
