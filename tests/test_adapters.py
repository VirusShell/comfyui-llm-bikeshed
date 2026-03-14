"""Tests for LLM backend adapters."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from adapters.ollama import OllamaAdapter


# ---------------------------------------------------------------------------
# Ollama adapter — name mapping
# ---------------------------------------------------------------------------


class TestOllamaNameMapping:
    """Verify canonical param names are mapped to Ollama-native names."""

    def test_max_tokens_mapped_to_num_predict(
        self, ollama_provider, mock_ollama_response, monkeypatch
    ):
        """max_tokens should become num_predict in the options object."""
        captured: dict = {}

        def fake_post(url, **kwargs):
            captured.update(kwargs)
            return mock_ollama_response

        monkeypatch.setattr("adapters.base.requests.post", fake_post)

        adapter = OllamaAdapter()
        adapter.generate(
            ollama_provider,
            [{"role": "user", "content": "hi"}],
            {"max_tokens": 256},
        )

        options = captured["json"]["options"]
        assert "num_predict" in options
        assert options["num_predict"] == 256
        assert "max_tokens" not in options

    def test_unmapped_allowed_param_passes_through(
        self, ollama_provider, mock_ollama_response, monkeypatch
    ):
        """Params already in Ollama's namespace pass through unchanged."""
        captured: dict = {}

        def fake_post(url, **kwargs):
            captured.update(kwargs)
            return mock_ollama_response

        monkeypatch.setattr("adapters.base.requests.post", fake_post)

        adapter = OllamaAdapter()
        adapter.generate(
            ollama_provider,
            [{"role": "user", "content": "hi"}],
            {"temperature": 0.7, "top_p": 0.9},
        )

        options = captured["json"]["options"]
        assert options["temperature"] == 0.7
        assert options["top_p"] == 0.9


# ---------------------------------------------------------------------------
# Ollama adapter — allowlist filtering
# ---------------------------------------------------------------------------


class TestOllamaAllowlistFiltering:
    """Unsupported params are silently dropped (logged at info)."""

    def test_unsupported_param_dropped(
        self, ollama_provider, mock_ollama_response, monkeypatch
    ):
        captured: dict = {}

        def fake_post(url, **kwargs):
            captured.update(kwargs)
            return mock_ollama_response

        monkeypatch.setattr("adapters.base.requests.post", fake_post)

        adapter = OllamaAdapter()
        adapter.generate(
            ollama_provider,
            [{"role": "user", "content": "hi"}],
            {"temperature": 0.5, "bogus_param": 42},
        )

        options = captured["json"]["options"]
        assert "bogus_param" not in options
        assert options["temperature"] == 0.5

    def test_empty_options_omits_options_key(
        self, ollama_provider, mock_ollama_response, monkeypatch
    ):
        """When all params are filtered out, options key is absent."""
        captured: dict = {}

        def fake_post(url, **kwargs):
            captured.update(kwargs)
            return mock_ollama_response

        monkeypatch.setattr("adapters.base.requests.post", fake_post)

        adapter = OllamaAdapter()
        adapter.generate(
            ollama_provider,
            [{"role": "user", "content": "hi"}],
            {"totally_unknown": 1},
        )

        assert "options" not in captured["json"]

    def test_no_options_omits_options_key(
        self, ollama_provider, mock_ollama_response, monkeypatch
    ):
        """Empty options dict results in no options key in payload."""
        captured: dict = {}

        def fake_post(url, **kwargs):
            captured.update(kwargs)
            return mock_ollama_response

        monkeypatch.setattr("adapters.base.requests.post", fake_post)

        adapter = OllamaAdapter()
        adapter.generate(
            ollama_provider,
            [{"role": "user", "content": "hi"}],
            {},
        )

        assert "options" not in captured["json"]


# ---------------------------------------------------------------------------
# Ollama adapter — payload structure
# ---------------------------------------------------------------------------


class TestOllamaPayloadStructure:
    """Verify the overall shape of the POST payload."""

    def test_basic_payload_structure(
        self, ollama_provider, mock_ollama_response, monkeypatch
    ):
        captured: dict = {}

        def fake_post(url, **kwargs):
            captured.update(kwargs)
            return mock_ollama_response

        monkeypatch.setattr("adapters.base.requests.post", fake_post)

        messages = [{"role": "user", "content": "hello"}]
        adapter = OllamaAdapter()
        adapter.generate(
            ollama_provider,
            messages,
            {"temperature": 0.8},
        )

        payload = captured["json"]
        assert payload["model"] == "llama3"
        assert payload["messages"] == messages
        assert payload["stream"] is False
        assert payload["options"] == {"temperature": 0.8}

    def test_options_nested_not_top_level(
        self, ollama_provider, mock_ollama_response, monkeypatch
    ):
        """Generation params go in nested options dict, not top-level."""
        captured: dict = {}

        def fake_post(url, **kwargs):
            captured.update(kwargs)
            return mock_ollama_response

        monkeypatch.setattr("adapters.base.requests.post", fake_post)

        adapter = OllamaAdapter()
        adapter.generate(
            ollama_provider,
            [{"role": "user", "content": "hi"}],
            {"temperature": 0.5, "seed": 42},
        )

        payload = captured["json"]
        # Params must be nested under options
        assert "temperature" not in payload
        assert "seed" not in payload
        assert payload["options"]["temperature"] == 0.5
        assert payload["options"]["seed"] == 42

    def test_endpoint_url_constructed_correctly(
        self, ollama_provider, mock_ollama_response, monkeypatch
    ):
        captured_url: list[str] = []

        def fake_post(url, **kwargs):
            captured_url.append(url)
            return mock_ollama_response

        monkeypatch.setattr("adapters.base.requests.post", fake_post)

        adapter = OllamaAdapter()
        adapter.generate(
            ollama_provider,
            [{"role": "user", "content": "hi"}],
            {},
        )

        assert captured_url[0] == "http://localhost:11434/api/chat"

    def test_url_trailing_slash_stripped(
        self, ollama_provider, mock_ollama_response, monkeypatch
    ):
        captured_url: list[str] = []

        def fake_post(url, **kwargs):
            captured_url.append(url)
            return mock_ollama_response

        monkeypatch.setattr("adapters.base.requests.post", fake_post)

        ollama_provider["url"] = "http://localhost:11434/"
        adapter = OllamaAdapter()
        adapter.generate(
            ollama_provider,
            [{"role": "user", "content": "hi"}],
            {},
        )

        assert captured_url[0] == "http://localhost:11434/api/chat"

    def test_response_text_extracted(
        self, ollama_provider, mock_ollama_response, monkeypatch
    ):
        monkeypatch.setattr(
            "adapters.base.requests.post",
            lambda url, **kw: mock_ollama_response,
        )

        adapter = OllamaAdapter()
        result = adapter.generate(
            ollama_provider,
            [{"role": "user", "content": "hi"}],
            {},
        )

        assert result == "Hello from Ollama!"

    def test_timeout_forwarded(
        self, ollama_provider, mock_ollama_response, monkeypatch
    ):
        captured: dict = {}

        def fake_post(url, **kwargs):
            captured.update(kwargs)
            return mock_ollama_response

        monkeypatch.setattr("adapters.base.requests.post", fake_post)

        ollama_provider["timeout"] = 60
        adapter = OllamaAdapter()
        adapter.generate(
            ollama_provider,
            [{"role": "user", "content": "hi"}],
            {},
        )

        assert captured["timeout"] == 60


# ---------------------------------------------------------------------------
# Ollama adapter — keep_alive behavior
# ---------------------------------------------------------------------------


class TestOllamaKeepAlive:
    """keep_alive is top-level in payload, not nested in options."""

    def test_keep_alive_from_provider_memory(
        self, ollama_provider, mock_ollama_response, monkeypatch
    ):
        captured: dict = {}

        def fake_post(url, **kwargs):
            captured.update(kwargs)
            return mock_ollama_response

        monkeypatch.setattr("adapters.base.requests.post", fake_post)

        adapter = OllamaAdapter()
        adapter.generate(
            ollama_provider,
            [{"role": "user", "content": "hi"}],
            {},
        )

        payload = captured["json"]
        assert payload["keep_alive"] == "30s"
        # Must be top-level, not in options
        assert "keep_alive" not in payload.get("options", {})

    def test_keep_alive_absent_when_not_configured(
        self, ollama_provider, mock_ollama_response, monkeypatch
    ):
        captured: dict = {}

        def fake_post(url, **kwargs):
            captured.update(kwargs)
            return mock_ollama_response

        monkeypatch.setattr("adapters.base.requests.post", fake_post)

        ollama_provider["memory"]["keep_alive"] = None
        adapter = OllamaAdapter()
        adapter.generate(
            ollama_provider,
            [{"role": "user", "content": "hi"}],
            {},
        )

        assert "keep_alive" not in captured["json"]

    def test_skip_unload_sets_5m_keep_alive(
        self, ollama_provider, mock_ollama_response, monkeypatch
    ):
        """Mid-chain calls use skip_unload=True -> keep_alive='5m'."""
        captured: dict = {}

        def fake_post(url, **kwargs):
            captured.update(kwargs)
            return mock_ollama_response

        monkeypatch.setattr("adapters.base.requests.post", fake_post)

        adapter = OllamaAdapter()
        adapter.generate(
            ollama_provider,
            [{"role": "user", "content": "hi"}],
            {},
            skip_unload=True,
        )

        assert captured["json"]["keep_alive"] == "5m"

    def test_skip_unload_overrides_provider_keep_alive(
        self, ollama_provider, mock_ollama_response, monkeypatch
    ):
        """skip_unload=True overrides whatever the provider configured."""
        captured: dict = {}

        def fake_post(url, **kwargs):
            captured.update(kwargs)
            return mock_ollama_response

        monkeypatch.setattr("adapters.base.requests.post", fake_post)

        # Provider says "10s" but skip_unload should override to "5m"
        ollama_provider["memory"]["keep_alive"] = "10s"
        adapter = OllamaAdapter()
        adapter.generate(
            ollama_provider,
            [{"role": "user", "content": "hi"}],
            {},
            skip_unload=True,
        )

        assert captured["json"]["keep_alive"] == "5m"


# ---------------------------------------------------------------------------
# Ollama adapter — error handling
# ---------------------------------------------------------------------------


class TestOllamaErrorHandling:
    """Adapter raises RuntimeError on HTTP errors."""

    def test_http_error_raises_runtime_error(
        self, ollama_provider, monkeypatch
    ):
        error_resp = MagicMock()
        error_resp.ok = False
        error_resp.status_code = 500
        error_resp.text = "Internal Server Error"

        monkeypatch.setattr(
            "adapters.base.requests.post",
            lambda url, **kw: error_resp,
        )

        adapter = OllamaAdapter()
        with pytest.raises(RuntimeError, match="Ollama error"):
            adapter.generate(
                ollama_provider,
                [{"role": "user", "content": "hi"}],
                {},
            )
