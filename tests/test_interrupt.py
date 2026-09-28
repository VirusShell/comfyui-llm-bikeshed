"""Tests for ComfyUI cancel / interrupt handling during HTTP requests."""

from __future__ import annotations

import threading
import time
from unittest.mock import MagicMock

import pytest

import adapters.interrupt as interrupt_mod
from adapters.base import _safe_post
from adapters.interrupt import interruptible_request
from adapters.oai_compat import OAICompatAdapter


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

    def test_calls_on_interrupt_callback(self, mock_comfy_interrupt, monkeypatch):
        started = threading.Event()
        called = {"value": False}

        class SlowResponse:
            def close(self) -> None:
                pass

            def iter_content(self, chunk_size: int = 8192):
                started.set()
                while True:
                    time.sleep(0.05)
                    yield b""

        def slow_request(self, method, url, **kwargs):
            kwargs.setdefault("stream", True)
            return SlowResponse()

        monkeypatch.setattr(
            interrupt_mod.requests.Session, "request", slow_request, raising=False
        )

        def on_interrupt() -> None:
            called["value"] = True

        result: dict[str, object] = {}

        def run() -> None:
            try:
                interruptible_request(
                    "POST",
                    "http://example.com/v1/chat/completions",
                    on_interrupt=on_interrupt,
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
        assert called["value"] is True

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


class TestOAICompatTextgenCancel:
    def test_textgen_cancel_calls_stop_generation(
        self, mock_comfy_interrupt, monkeypatch,
    ):
        """Cancel during Textgen chat POST must call stop-generation."""
        started = threading.Event()
        stop_urls: list[str] = []

        class SlowResponse:
            def close(self) -> None:
                pass

            def iter_content(self, chunk_size: int = 8192):
                started.set()
                while True:
                    time.sleep(0.05)
                    yield b""

        def slow_request(self, method, url, **kwargs):
            kwargs.setdefault("stream", True)
            return SlowResponse()

        def track_stop(url, **kwargs):
            stop_urls.append(url)
            resp = MagicMock()
            resp.ok = True
            resp.status_code = 200
            return resp

        monkeypatch.setattr(
            interrupt_mod.requests.Session, "request", slow_request, raising=False
        )
        monkeypatch.setattr("adapters.oai_compat.requests.post", track_stop)
        monkeypatch.setattr(
            "adapters.oai_compat.resolve_provider_auth",
            lambda _p: ("test-api-key", "test-admin-key"),
        )

        provider = {
            "backend": "text_gen_webui",
            "adapter": "oai_compat",
            "url": "http://localhost:5000",
            "model": "my-model",
            "timeout": 120,
            "lifecycle": None,
            "load_before_generate": False,
        }

        adapter = OAICompatAdapter()
        result: dict[str, object] = {}

        def run() -> None:
            try:
                adapter.generate(
                    provider,
                    [{"role": "user", "content": "hi"}],
                    {},
                    skip_unload=True,
                )
            except BaseException as exc:
                result["exc"] = exc

        thread = threading.Thread(target=run, daemon=True)
        thread.start()
        assert started.wait(timeout=2.0)

        mock_comfy_interrupt["interrupted"] = True
        thread.join(timeout=2.0)

        assert isinstance(result.get("exc"), InterruptProcessingException)
        assert len(stop_urls) == 1
        assert stop_urls[0] == "http://localhost:5000/v1/internal/stop-generation"


class TestUnloadOnInterruptPolicy:
    """Q5: unload on cancel only when asked, and only if lifecycle is embedded."""

    def _raise_interrupt(self, *_args, **_kwargs):
        raise InterruptProcessingException()

    def test_flag_on_unloads_when_lifecycle_present(
        self, monkeypatch, text_gen_webui_provider
    ):
        monkeypatch.setattr("adapters.oai_compat._safe_post", self._raise_interrupt)
        monkeypatch.setattr("adapters.oai_compat._safe_get", self._raise_interrupt)
        unloads: list[str] = []
        adapter = OAICompatAdapter()
        monkeypatch.setattr(
            adapter,
            "_unload_model_text_gen_webui",
            lambda _provider: unloads.append("unload"),
        )
        with pytest.raises(InterruptProcessingException):
            adapter.generate(
                text_gen_webui_provider,
                [{"role": "user", "content": "hi"}],
                {},
                skip_unload=True,
                unload_on_interrupt=True,
            )
        assert unloads == ["unload"]

    def test_flag_off_does_not_unload(
        self, monkeypatch, text_gen_webui_provider
    ):
        monkeypatch.setattr("adapters.oai_compat._safe_post", self._raise_interrupt)
        monkeypatch.setattr("adapters.oai_compat._safe_get", self._raise_interrupt)
        unloads: list[str] = []
        adapter = OAICompatAdapter()
        monkeypatch.setattr(
            adapter,
            "_unload_model_text_gen_webui",
            lambda _provider: unloads.append("unload"),
        )
        with pytest.raises(InterruptProcessingException):
            adapter.generate(
                text_gen_webui_provider,
                [{"role": "user", "content": "hi"}],
                {},
            )
        assert unloads == []

    def test_manage_vram_off_does_not_unload(self, monkeypatch):
        """No lifecycle means Manage VRAM OFF; the property cannot force unload."""
        monkeypatch.setattr("adapters.oai_compat._safe_post", self._raise_interrupt)
        unloads: list[str] = []
        adapter = OAICompatAdapter()
        monkeypatch.setattr(
            adapter,
            "_unload_model_text_gen_webui",
            lambda _provider: unloads.append("unload"),
        )
        provider = {
            "backend": "text_gen_webui",
            "adapter": "oai_compat",
            "url": "http://localhost:5000",
            "model": "my-model",
            "timeout": 120,
            "lifecycle": None,
            "load_before_generate": False,
        }
        with pytest.raises(InterruptProcessingException):
            adapter.generate(
                provider,
                [{"role": "user", "content": "hi"}],
                {},
                unload_on_interrupt=True,
            )
        assert unloads == []

    def test_non_interrupt_error_does_not_unload(
        self, monkeypatch, text_gen_webui_provider
    ):
        def boom(*_args, **_kwargs):
            raise RuntimeError("HTTP 500 — no")

        monkeypatch.setattr("adapters.oai_compat._safe_post", boom)
        monkeypatch.setattr("adapters.oai_compat._safe_get", boom)
        unloads: list[str] = []
        adapter = OAICompatAdapter()
        monkeypatch.setattr(
            adapter,
            "_unload_model_text_gen_webui",
            lambda _provider: unloads.append("unload"),
        )
        with pytest.raises(RuntimeError, match="HTTP 500"):
            adapter.generate(
                text_gen_webui_provider,
                [{"role": "user", "content": "hi"}],
                {},
                unload_on_interrupt=True,
            )
        assert unloads == []
