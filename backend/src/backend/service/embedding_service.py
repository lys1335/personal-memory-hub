"""EmbeddingService — Generate embeddings using Ollama nomic-embed-text."""
from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Generate text embeddings via Ollama (nomic-embed-text)."""

    def __init__(self, ollama_base_url: str = "http://localhost:11434", model: str = "nomic-embed-text") -> None:
        self._base_url = ollama_base_url.rstrip("/")
        self._model = model

    async def generate(self, text: str) -> list[float] | None:
        """Generate embedding for a single text."""
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(
                    f"{self._base_url}/api/embeddings",
                    json={"model": self._model, "prompt": text[:4000]},
                )
                if resp.status_code == 200:
                    return resp.json()["embedding"]
                logger.error("Embedding failed: %s", resp.text[:200])
                return None
        except Exception as exc:
            logger.error("Embedding exception: %s", exc)
            return None
