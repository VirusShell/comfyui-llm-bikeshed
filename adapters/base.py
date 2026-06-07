"""Base adapter protocol and shared helpers for LLM backends."""

from __future__ import annotations

import math
from typing import Protocol

import requests

from .interrupt import (
    check_before_request,
    comfy_interrupt_available,
    interruptible_request,
)


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


def _request_with_errors(
    method: str,
    url: str,
    backend: str,
    **kwargs: object,
) -> requests.Response:
    """Send HTTP request with interrupt, timeout, and connection error handling."""
    try:
        if comfy_interrupt_available():
            resp = interruptible_request(method, url, **kwargs)  # type: ignore[arg-type]
        elif method.upper() == "GET":
            resp = requests.get(url, **kwargs)  # type: ignore[arg-type]
        else:
            resp = requests.post(url, **kwargs)  # type: ignore[arg-type]
        return resp
    except requests.Timeout:
        raise RuntimeError(
            f"[llm-bikeshed] {backend} request timed out at {url}"
        ) from None
    except requests.ConnectionError:
        raise RuntimeError(
            f"[llm-bikeshed] {backend} is offline or unreachable at {url}"
        ) from None


def _safe_get(
    url: str,
    backend: str,
    **kwargs: object,
) -> requests.Response:
    """Send GET request with interrupt; connection errors propagate to caller."""
    check_before_request()
    if comfy_interrupt_available():
        return interruptible_request("GET", url, **kwargs)  # type: ignore[arg-type]
    try:
        return requests.get(url, **kwargs)  # type: ignore[arg-type]
    except requests.Timeout:
        raise RuntimeError(
            f"[llm-bikeshed] {backend} request timed out at {url}"
        ) from None


def _safe_post(
    url: str,
    backend: str,
    **kwargs: object,
) -> requests.Response:
    """Send POST request with interrupt and structured error handling."""
    if "json" in kwargs and kwargs["json"] is not None:
        kwargs["json"] = _sanitize_payload(kwargs["json"])
    check_before_request()
    return _request_with_errors("POST", url, backend, **kwargs)
