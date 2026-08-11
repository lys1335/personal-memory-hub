"""ReflectionProvider — LLM provider abstraction for ReflectionEngine.

Per D4.2d §2.7: "LLM invocation — Service manages AI provider communication"
ReflectionEngine must NOT depend on concrete LLM implementations.

This module provides:
- ReflectionProvider protocol (abstract interface)
- LocalLlmProvider (local LLM via Ollama-compatible API)
- MockReflectionProvider (for testing)

Future: OpenAIReflectionProvider, AzureReflectionProvider, etc.
"""

from __future__ import annotations

import asyncio
import json
import logging
import urllib.request
import urllib.error
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


class LocalLlmProvider(ReflectionProvider):
    """Local LLM provider using Ollama-compatible API.

    This is the default implementation for local LLM inference.
    Configuration via environment variables:
    - PMH_LLM_BASE_URL (default: "http://host.docker.internal:11434")
    - PMH_REFLECTION_MODEL (default: "fact-extractor:v5")
    """

    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        timeout: float = 120.0,
    ) -> None:
        self.base_url = (
            base_url
            or __import__("os").environ.get("PMH_LLM_BASE_URL", "http://host.docker.internal:11434")
        ).rstrip("/")
        self.model = model or __import__("os").environ.get("PMH_REFLECTION_MODEL", "local-model")
        self.timeout = timeout
        self._log = logging.getLogger(f"{__name__}.LocalLlm")

    async def _wait_for_llm(self, retries: int = 3, delay: int = 2) -> None:
        """Wait for LLM to be ready and model loaded."""
        try:
            import httpx
        except ImportError:
            return

        for i in range(retries):
            try:
                async with httpx.AsyncClient(timeout=httpx.Timeout(5.0)) as client:
                    resp = await client.get(f"{self.base_url}/api/tags")
                    if resp.status_code == 200:
                        models = resp.json().get("models", [])
                        model_names = [m.get("name", "") for m in models]
                        if self.model in model_names:
                            self._log.info(f"LLM ready, model {self.model} loaded")
                            return
                        self._log.warning(f"LLM ready but model {self.model} not found, waiting...")
                    else:
                        self._log.warning(f"LLM returned status {resp.status_code}, waiting...")
            except Exception as e:
                self._log.warning(f"LLM not ready (attempt {i+1}/{retries}): {e}")
            if i < retries - 1:
                await asyncio.sleep(delay)

    async def generate(self, prompt: str, context: dict[str, Any]) -> dict[str, Any]:
        """Call local LLM API with structured prompt."""
        # Wait for LLM to be ready
        await self._wait_for_llm(retries=5, delay=5)

        system_prompt = prompt

        # Build the structured prompt if context has candidates
        if context and "candidates" in context:
            candidates = context["candidates"]
            structured_prompt = f"""You are a fact extraction engine. Extract facts from the following candidates.

Candidates:
{json.dumps(candidates, ensure_ascii=False, indent=2)}

Extract facts in this exact JSON format:
{{
  "facts": [
    {{"entity": "entity name", "value": "fact value", "confidence": 0.9}}
  ]
}}

Return ONLY valid JSON, no explanations."""
        else:
            structured_prompt = system_prompt

        url = f"{self.base_url}/api/generate"

        # Retry logic for model loading
        max_retries = 3
        for attempt in range(max_retries):
            try:
                import httpx

                payload = {
                    "model": self.model,
                    "prompt": structured_prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.1,
                        "num_predict": 2048,
                    },
                }

                self._log.info("Calling LLM: model=%s, url=%s", self.model, url)

                async with httpx.AsyncClient(timeout=httpx.Timeout(self.timeout)) as client:
                    resp = await client.post(url, json=payload)
                    if resp.status_code == 404:
                        self._log.warning(f"LLM returned 404 (attempt {attempt+1}/{max_retries}), waiting 10s...")
                        await asyncio.sleep(10)
                        await self._wait_for_llm(retries=3, delay=5)
                        continue

                    resp.raise_for_status()
                    data = resp.json()

                # Parse response
                response_text = data.get("response", "")
                return self._parse_response(response_text)

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404 and attempt < max_retries - 1:
                    self._log.warning(f"LLM returned 404 (attempt {attempt+1}/{max_retries}), waiting 10s...")
                    await asyncio.sleep(10)
                    continue
                raise
            except Exception as e:
                self._log.error(f"LLM call failed: {e}")
                if attempt < max_retries - 1:
                    self._log.info(f"Retrying LLM call (attempt {attempt+2}/{max_retries})...")
                    await asyncio.sleep(5)
                    continue
                raise

        # Fallback: use urllib for compatibility
        return await self._generate_urllib(structured_prompt)

    async def _generate_urllib(self, prompt: str) -> dict[str, Any]:
        """Fallback using urllib for environments without httpx."""
        url = f"{self.base_url}/api/generate"
        payload = json.dumps({
            "model": self.model,
            "prompt": prompt,
            "stream": False,
        }).encode("utf-8")

        self._log.info("Calling LLM (urllib): model=%s, url=%s", self.model, url)

        try:
            req = urllib.request.Request(
                url,
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                response_text = data.get("response", "")
                return self._parse_response(response_text)
        except Exception as e:
            self._log.error("LLM connection failed: %s", e)
            return {"facts": []}

    def _parse_response(self, response_text: str) -> dict[str, Any]:
        """Parse LLM response into structured facts."""
        # Try to extract JSON from response
        response_text = response_text.strip()

        # Find JSON block
        start = response_text.find("{")
        end = response_text.rfind("}")
        if start != -1 and end != -1:
            response_text = response_text[start : end + 1]

        try:
            data = json.loads(response_text)
            return data
        except json.JSONDecodeError as e:
            self._log.error(f"Failed to parse LLM response: {e}")
            # Return empty facts
            return {"facts": []}


class MockReflectionProvider(ReflectionProvider):
    """Mock provider for testing."""

    def __init__(self, facts: list[dict[str, Any]] | None = None) -> None:
        self.facts = facts or []

    async def generate(self, prompt: str, context: dict[str, Any]) -> dict[str, Any]:
        return {"facts": self.facts}
