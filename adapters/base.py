"""Base adapter protocol and shared helpers for LLM backends."""

from __future__ import annotations

from typing import Protocol

import requests


class LLMAdapter(Protocol):
    """Protocol for LLM backend adapters."""

    def generate(
        self,
        provider: dict,
        messages: list[dict],
        options: dict,
        skip_unload: bool = False,
    ) -> str:
        """Send generation request. Returns extracted text."""
        ...


def _raise_on_error(response: requests.Response, backend: str, url: str) -> None:
    """Raise descriptive exception on HTTP error."""
    if not response.ok:
        try:
            body = response.text[:500]
        except Exception:
            body = "(could not read response body)"
        raise RuntimeError(
            f"[llm-bikeshed] {backend} error at {url}: "
            f"HTTP {response.status_code} — {body}"
        )
