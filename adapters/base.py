"""Base adapter protocol and shared helpers for LLM backends."""

from __future__ import annotations

import math
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


def _is_json_safe(value: object) -> bool:
    """Return False if value is a float NaN or Inf (not JSON-serializable)."""
    return not (isinstance(value, float) and (math.isnan(value) or math.isinf(value)))


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


def _sanitize_payload(obj: object) -> object:
    """Recursively replace NaN/Inf floats with None in a JSON payload."""
    if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
        return None
    if isinstance(obj, dict):
        return {k: _sanitize_payload(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_sanitize_payload(v) for v in obj]
    return obj


def _safe_post(
    url: str,
    backend: str,
    **kwargs: object,
) -> requests.Response:
    """Send POST request with structured error handling for timeout/connection."""
    if "json" in kwargs and kwargs["json"] is not None:
        kwargs["json"] = _sanitize_payload(kwargs["json"])
    try:
        return requests.post(url, **kwargs)  # type: ignore[arg-type]
    except requests.Timeout:
        raise RuntimeError(
            f"[llm-bikeshed] {backend} request timed out at {url}"
        ) from None
    except requests.ConnectionError:
        raise RuntimeError(
            f"[llm-bikeshed] {backend} is offline or unreachable at {url}"
        ) from None
