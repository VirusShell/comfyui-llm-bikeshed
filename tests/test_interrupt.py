"""Tests for ComfyUI cancel / interrupt handling during HTTP requests."""

from __future__ import annotations

import threading
import time
from unittest.mock import MagicMock

import pytest

import adapters.interrupt as interrupt_mod
from adapters.base import _safe_post
from adapters.interrupt import interruptible_request


class InterruptProcessingException(BaseException):
    """Test stand-in for comfy.model_management.InterruptProcessingException."""


@pytest.fixture()
def mock_comfy_interrupt(monkeypatch):
    """Inject ComfyUI-style interrupt hooks into adapters.interrupt."""
    state = {"interrupted": False}

    def processing_interrupted() -> bool:
        return state["interrupted"]

    def throw_exception_if_processing_interrupted() -> None:
        if state["interrupted"]:
            state["interrupted"] = False
            raise InterruptProcessingException()

    monkeypatch.setattr(interrupt_mod, "_comfy_loaded", True)
    monkeypatch.setattr(
        interrupt_mod, "_processing_interrupted", processing_interrupted
    )
    monkeypatch.setattr(
        interrupt_mod,
        "_throw_if_interrupted",
        throw_exception_if_processing_interrupted,
    )
    monkeypatch.setattr(
        "adapters.base.comfy_interrupt_available", lambda: True, raising=False
    )
    return state


class TestInterruptibleRequest:
    def test_raises_before_request_when_already_interrupted(
        self, mock_comfy_interrupt
    ):
        mock_comfy_interrupt["interrupted"] = True
        with pytest.raises(InterruptProcessingException):
            interruptible_request("POST", "http://example.com/v1/chat/completions")

    def test_cancels_inflight_request(self, mock_comfy_interrupt, monkeypatch):
        started = threading.Event()
        release = threading.Event()
        closed = {"value": False}

        class SlowResponse:
            def __init__(self) -> None:
                self.raw = MagicMock()

            def close(self) -> None:
                closed["value"] = True

            def iter_content(self, chunk_size: int = 8192):
                started.set()
                while not release.is_set():
                    time.sleep(0.05)
                yield b'{"choices":[{"message":{"content":"hi"}}]}'

        def slow_request(self, method, url, **kwargs):
            kwargs.setdefault("stream", True)
            return SlowResponse()

        monkeypatch.setattr(
            interrupt_mod.requests.Session, "request", slow_request, raising=False
        )

        result: dict[str, object] = {}

        def run() -> None:
            try:
                interruptible_request(
                    "POST",
                    "http://example.com/v1/chat/completions",
                    timeout=30,
                )
            except BaseException as exc:
                result["exc"] = exc

        thread = threading.Thread(target=run, daemon=True)
        thread.start()
        assert started.wait(timeout=2.0)

        mock_comfy_interrupt["interrupted"] = True
        thread.join(timeout=2.0)

        assert isinstance(result.get("exc"), InterruptProcessingException)
        assert closed["value"] is True

    def test_safe_post_uses_direct_requests_outside_comfy(
        self, monkeypatch, mock_oai_response
    ):
        monkeypatch.setattr(interrupt_mod, "_comfy_loaded", True)
        monkeypatch.setattr(interrupt_mod, "_processing_interrupted", None)
        monkeypatch.setattr(interrupt_mod, "_throw_if_interrupted", None)
        monkeypatch.setattr(
            "adapters.base.comfy_interrupt_available", lambda: False, raising=False
        )

        captured: dict = {}

        def fake_post(url, **kwargs):
            captured["url"] = url
            return mock_oai_response

        monkeypatch.setattr("adapters.base.requests.post", fake_post)

        resp = _safe_post(
            "http://localhost:1234/v1/chat/completions",
            "lm_studio",
            json={"model": "x"},
            timeout=10,
        )
        assert resp is mock_oai_response
        assert captured["url"].endswith("/v1/chat/completions")
