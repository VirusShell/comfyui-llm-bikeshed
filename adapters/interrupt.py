"""ComfyUI execution interrupt support for blocking HTTP requests."""

from __future__ import annotations

import threading
from typing import Any, Callable

import requests

_comfy_loaded = False
_processing_interrupted: Callable[[], bool] | None = None
_throw_if_interrupted: Callable[[], None] | None = None


def _load_comfy_interrupt() -> None:
    global _comfy_loaded, _processing_interrupted, _throw_if_interrupted
    if _comfy_loaded:
        return
    _comfy_loaded = True
    try:
        from comfy.model_management import (
            processing_interrupted,
            throw_exception_if_processing_interrupted,
        )
    except ImportError:
        return
    _processing_interrupted = processing_interrupted
    _throw_if_interrupted = throw_exception_if_processing_interrupted


def comfy_interrupt_available() -> bool:
    """Return True when ComfyUI interrupt hooks are importable."""
    _load_comfy_interrupt()
    return _processing_interrupted is not None


def check_before_request() -> None:
    """Raise ComfyUI InterruptProcessingException if cancel was requested."""
    _load_comfy_interrupt()
    if _throw_if_interrupted is not None:
        _throw_if_interrupted()


def is_processing_interrupted() -> bool:
    """Return True when ComfyUI has signalled cancel."""
    _load_comfy_interrupt()
    if _processing_interrupted is not None:
        return _processing_interrupted()
    return False


def _raise_interrupt() -> None:
    """Raise ComfyUI interrupt exception (never returns)."""
    _load_comfy_interrupt()
    if _throw_if_interrupted is not None:
        _throw_if_interrupted()
    raise RuntimeError("Processing interrupted")


def interruptible_request(
    method: str,
    url: str,
    *,
    poll_interval: float = 0.25,
    on_interrupt: Callable[[], None] | None = None,
    **kwargs: Any,
) -> requests.Response:
    """Run a blocking HTTP request that responds to ComfyUI cancel.

    Outside ComfyUI (tests, scripts), falls back to a direct ``requests`` call.
    """
    check_before_request()
    _load_comfy_interrupt()
    if _processing_interrupted is None:
        return requests.request(method, url, **kwargs)

    holder: dict[str, Any] = {"response": None, "error": None, "body": None}
    done = threading.Event()
    session = requests.Session()
    cancelled = False

    def worker() -> None:
        try:
            kwargs.setdefault("stream", True)
            resp = session.request(method, url, **kwargs)
            holder["response"] = resp
            chunks: list[bytes] = []
            for chunk in resp.iter_content(chunk_size=8192):
                if chunk:
                    chunks.append(chunk)
            holder["body"] = b"".join(chunks)
        except Exception as exc:
            holder["error"] = exc
        finally:
            done.set()

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()

    while not done.wait(timeout=poll_interval):
        if is_processing_interrupted():
            cancelled = True
            if on_interrupt is not None:
                try:
                    on_interrupt()
                except Exception:
                    pass  # Best-effort host stop; cancel must still propagate.
            resp = holder.get("response")
            if resp is not None:
                resp.close()
            session.close()
            _raise_interrupt()

    thread.join(timeout=poll_interval)

    if cancelled or is_processing_interrupted():
        _raise_interrupt()

    error = holder.get("error")
    if error is not None:
        raise error

    resp = holder["response"]
    if resp is None:
        raise requests.ConnectionError(f"No response from {url}")

    resp._content = holder["body"]
    return resp
