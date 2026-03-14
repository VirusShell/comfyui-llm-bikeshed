"""Tests for LLM backend adapters."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from adapters.oai_compat import OAICompatAdapter
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


# ---------------------------------------------------------------------------
# OAI-compat adapter — LM Studio path: allowlist filtering
# ---------------------------------------------------------------------------


class TestLMStudioAllowlistFiltering:
    """LM Studio params are filtered through the lm_studio allowlist."""

    def _lm_studio_provider(self) -> dict:
        """LM Studio provider with numeric TTL."""
        return {
            "backend": "lm_studio",
            "adapter": "oai_compat",
            "url": "http://localhost:1234",
            "model": "test-model",
            "timeout": 120,
            "api_key": None,
            "admin_key": None,
            "memory": {"ttl": 30, "keep_alive": None},
        }

    def test_lm_studio_allowed_params_forwarded(
        self, mock_oai_response, monkeypatch
    ):
        """Allowed params appear top-level in OAI payload (not nested)."""
        captured: dict = {}

        def fake_post(url, **kwargs):
            captured.update(kwargs)
            return mock_oai_response

        monkeypatch.setattr("adapters.base.requests.post", fake_post)

        adapter = OAICompatAdapter()
        adapter.generate(
            self._lm_studio_provider(),
            [{"role": "user", "content": "hi"}],
            {"temperature": 0.7, "top_p": 0.9, "seed": 42},
        )

        payload = captured["json"]
        assert payload["temperature"] == 0.7
        assert payload["top_p"] == 0.9
        assert payload["seed"] == 42

    def test_lm_studio_unsupported_param_dropped(
        self, mock_oai_response, monkeypatch
    ):
        """Params not in lm_studio allowlist are silently dropped."""
        captured: dict = {}

        def fake_post(url, **kwargs):
            captured.update(kwargs)
            return mock_oai_response

        monkeypatch.setattr("adapters.base.requests.post", fake_post)

        adapter = OAICompatAdapter()
        adapter.generate(
            self._lm_studio_provider(),
            [{"role": "user", "content": "hi"}],
            {"temperature": 0.5, "min_p": 0.1, "tfs": 0.9},
        )

        payload = captured["json"]
        assert payload["temperature"] == 0.5
        assert "min_p" not in payload
        assert "tfs" not in payload

    def test_lm_studio_all_params_filtered_leaves_clean_payload(
        self, mock_oai_response, monkeypatch
    ):
        """When all params are unsupported, payload has no extra keys."""
        captured: dict = {}

        def fake_post(url, **kwargs):
            captured.update(kwargs)
            return mock_oai_response

        monkeypatch.setattr("adapters.base.requests.post", fake_post)

        adapter = OAICompatAdapter()
        adapter.generate(
            self._lm_studio_provider(),
            [{"role": "user", "content": "hi"}],
            {"totally_bogus": 99},
        )

        payload = captured["json"]
        assert "totally_bogus" not in payload
        # Core keys still present
        assert payload["model"] == "test-model"
        assert payload["stream"] is False


# ---------------------------------------------------------------------------
# OAI-compat adapter — LM Studio path: TTL in payload
# ---------------------------------------------------------------------------


class TestLMStudioTTL:
    """LM Studio TTL appears as top-level 'ttl' key in payload."""

    def _lm_studio_provider(self, ttl: int = 30) -> dict:
        return {
            "backend": "lm_studio",
            "adapter": "oai_compat",
            "url": "http://localhost:1234",
            "model": "test-model",
            "timeout": 120,
            "api_key": None,
            "admin_key": None,
            "memory": {"ttl": ttl, "keep_alive": None},
        }

    def test_lm_studio_ttl_in_payload(
        self, mock_oai_response, monkeypatch
    ):
        """TTL from provider memory is forwarded in payload."""
        captured: dict = {}

        def fake_post(url, **kwargs):
            captured.update(kwargs)
            return mock_oai_response

        monkeypatch.setattr("adapters.base.requests.post", fake_post)

        adapter = OAICompatAdapter()
        adapter.generate(
            self._lm_studio_provider(ttl=30),
            [{"role": "user", "content": "hi"}],
            {},
        )

        assert captured["json"]["ttl"] == 30

    def test_lm_studio_ttl_absent_when_none(
        self, mock_oai_response, monkeypatch
    ):
        """TTL omitted from payload when provider has ttl=None."""
        captured: dict = {}

        def fake_post(url, **kwargs):
            captured.update(kwargs)
            return mock_oai_response

        monkeypatch.setattr("adapters.base.requests.post", fake_post)

        provider = self._lm_studio_provider()
        provider["memory"]["ttl"] = None
        adapter = OAICompatAdapter()
        adapter.generate(
            provider,
            [{"role": "user", "content": "hi"}],
            {},
        )

        assert "ttl" not in captured["json"]

    def test_lm_studio_mid_chain_ttl_extension(
        self, mock_oai_response, monkeypatch
    ):
        """skip_unload=True extends TTL to max(ttl*10, 300)."""
        captured: dict = {}

        def fake_post(url, **kwargs):
            captured.update(kwargs)
            return mock_oai_response

        monkeypatch.setattr("adapters.base.requests.post", fake_post)

        adapter = OAICompatAdapter()
        adapter.generate(
            self._lm_studio_provider(ttl=30),
            [{"role": "user", "content": "hi"}],
            {},
            skip_unload=True,
        )

        # max(30*10, 300) = 300
        assert captured["json"]["ttl"] == 300

    def test_lm_studio_mid_chain_ttl_extension_large_ttl(
        self, mock_oai_response, monkeypatch
    ):
        """When base TTL is large, extended TTL = ttl*10."""
        captured: dict = {}

        def fake_post(url, **kwargs):
            captured.update(kwargs)
            return mock_oai_response

        monkeypatch.setattr("adapters.base.requests.post", fake_post)

        adapter = OAICompatAdapter()
        adapter.generate(
            self._lm_studio_provider(ttl=60),
            [{"role": "user", "content": "hi"}],
            {},
            skip_unload=True,
        )

        # max(60*10, 300) = 600
        assert captured["json"]["ttl"] == 600


# ---------------------------------------------------------------------------
# OAI-compat adapter — LM Studio path: auth headers
# ---------------------------------------------------------------------------


class TestLMStudioAuthHeaders:
    """Auth header behavior for LM Studio backend."""

    def _lm_studio_provider(self, api_key: str | None = None) -> dict:
        return {
            "backend": "lm_studio",
            "adapter": "oai_compat",
            "url": "http://localhost:1234",
            "model": "test-model",
            "timeout": 120,
            "api_key": api_key,
            "admin_key": None,
            "memory": {"ttl": 30, "keep_alive": None},
        }

    def test_lm_studio_no_auth_header_when_no_key(
        self, mock_oai_response, monkeypatch
    ):
        """No Authorization header when api_key is None."""
        captured: dict = {}

        def fake_post(url, **kwargs):
            captured.update(kwargs)
            return mock_oai_response

        monkeypatch.setattr("adapters.base.requests.post", fake_post)

        adapter = OAICompatAdapter()
        adapter.generate(
            self._lm_studio_provider(api_key=None),
            [{"role": "user", "content": "hi"}],
            {},
        )

        headers = captured["headers"]
        assert "Authorization" not in headers

    def test_lm_studio_auth_header_when_key_set(
        self, mock_oai_response, monkeypatch
    ):
        """Authorization Bearer header present when api_key is set."""
        captured: dict = {}

        def fake_post(url, **kwargs):
            captured.update(kwargs)
            return mock_oai_response

        monkeypatch.setattr("adapters.base.requests.post", fake_post)

        adapter = OAICompatAdapter()
        adapter.generate(
            self._lm_studio_provider(api_key="sk-test-123"),
            [{"role": "user", "content": "hi"}],
            {},
        )

        headers = captured["headers"]
        assert headers["Authorization"] == "Bearer sk-test-123"


# ---------------------------------------------------------------------------
# OAI-compat adapter — LM Studio path: payload structure
# ---------------------------------------------------------------------------


class TestLMStudioPayloadStructure:
    """Verify OAI-compat payload shape for LM Studio."""

    def _lm_studio_provider(self) -> dict:
        return {
            "backend": "lm_studio",
            "adapter": "oai_compat",
            "url": "http://localhost:1234",
            "model": "test-model",
            "timeout": 120,
            "api_key": None,
            "admin_key": None,
            "memory": {"ttl": 30, "keep_alive": None},
        }

    def test_lm_studio_endpoint_url(
        self, mock_oai_response, monkeypatch
    ):
        """Endpoint is {url}/v1/chat/completions."""
        captured_url: list[str] = []

        def fake_post(url, **kwargs):
            captured_url.append(url)
            return mock_oai_response

        monkeypatch.setattr("adapters.base.requests.post", fake_post)

        adapter = OAICompatAdapter()
        adapter.generate(
            self._lm_studio_provider(),
            [{"role": "user", "content": "hi"}],
            {},
        )

        assert captured_url[0] == "http://localhost:1234/v1/chat/completions"

    def test_lm_studio_response_text_extracted(
        self, mock_oai_response, monkeypatch
    ):
        """Response text extracted from OAI choices[0].message.content."""
        monkeypatch.setattr(
            "adapters.base.requests.post",
            lambda url, **kw: mock_oai_response,
        )

        adapter = OAICompatAdapter()
        result = adapter.generate(
            self._lm_studio_provider(),
            [{"role": "user", "content": "hi"}],
            {},
        )

        assert result == "Hello from the model!"

    def test_lm_studio_error_raises_runtime_error(self, monkeypatch):
        """HTTP errors raise RuntimeError with backend context."""
        error_resp = MagicMock()
        error_resp.ok = False
        error_resp.status_code = 500
        error_resp.text = "Internal Server Error"

        monkeypatch.setattr(
            "adapters.base.requests.post",
            lambda url, **kw: error_resp,
        )

        adapter = OAICompatAdapter()
        with pytest.raises(RuntimeError, match="lm_studio error"):
            adapter.generate(
                self._lm_studio_provider(),
                [{"role": "user", "content": "hi"}],
                {},
            )
