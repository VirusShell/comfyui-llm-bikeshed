"""Ollama Native adapter for /api/chat endpoint."""

from __future__ import annotations

import logging

from .base import _is_json_safe, _raise_on_error, _safe_post

logger = logging.getLogger("llm-bikeshed")


class OllamaAdapter:
    """Adapter for Ollama's native /api/chat endpoint."""

    # Params that go in the `options` object.
    ALLOWED_OPTIONS: set[str] = {
        "temperature",
        "top_k",
        "top_p",
        "min_p",
        "seed",
        "num_predict",
        "num_ctx",
        "stop",
        "repeat_penalty",
        "repeat_last_n",
        "presence_penalty",
        "frequency_penalty",
        "mirostat",
        "mirostat_eta",
        "mirostat_tau",
        "tfs_z",
        "typical_p",
    }

    # Name mapping: canonical name -> Ollama name.
    NAME_MAP: dict[str, str] = {
        "max_tokens": "num_predict",
    }

    def generate(
        self,
        provider: dict,
        messages: list[dict],
        options: dict,
        skip_unload: bool = False,
    ) -> str:
        """Send a chat request to Ollama and return the generated text."""
        url: str = provider["url"]
        model: str = provider["model"]
        timeout: int = provider.get("timeout", 120)

        # Map and filter options into Ollama's `options` object.
        ollama_options: dict = {}
        for key, value in options.items():
            if not _is_json_safe(value):
                logger.warning(
                    "Dropping non-JSON-safe param '%s' (value=%r) for Ollama",
                    key,
                    value,
                )
                continue
            mapped_key = self.NAME_MAP.get(key, key)
            if mapped_key in self.ALLOWED_OPTIONS:
                ollama_options[mapped_key] = value
            else:
                logger.info(
                    "Dropping unsupported param '%s' for Ollama", key
                )

        # Build payload.
        payload: dict = {
            "model": model,
            "messages": messages,
            "stream": False,
        }

        if ollama_options:
            payload["options"] = ollama_options

        # Memory management: keep_alive is top-level.
        if skip_unload:
            payload["keep_alive"] = "5m"  # longer TTL for mid-chain
        else:
            keep_alive = provider.get("memory", {}).get("keep_alive")
            if keep_alive is not None:
                payload["keep_alive"] = keep_alive

        # Send request.
        endpoint = f"{url.rstrip('/')}/api/chat"
        response = _safe_post(
            endpoint, "Ollama", json=payload, timeout=timeout
        )

        _raise_on_error(response, "Ollama", endpoint)

        return response.json()["message"]["content"]
