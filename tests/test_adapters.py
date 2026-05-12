"""Tests for LLM backend adapters."""

from __future__ import annotations

from unittest.mock import MagicMock, PropertyMock

import pytest
import requests

from adapters.base import _raise_on_error
from adapters.oai_compat import OAICompatAdapter

# ---------------------------------------------------------------------------
# _raise_on_error helper
# ---------------------------------------------------------------------------


class TestRaiseOnError:
    """Test the _raise_on_error helper from adapters.base."""

    def _make_response(
        self, status_code: int, text: str = "", ok: bool | None = None
    ) -> MagicMock:
        resp = MagicMock()
        resp.status_code = status_code
        resp.ok = ok if ok is not None else (200 <= status_code < 400)
        resp.text = text
        return resp

    def test_4xx_raises_with_backend_name(self):
        resp = self._make_response(404, "Not Found")
        with pytest.raises(RuntimeError, match="Acme"):
            _raise_on_error(resp, "Acme", "http://localhost:9999/v1/chat")

    def test_4xx_raises_with_url(self):
        resp = self._make_response(400, "Bad Request")
        with pytest.raises(RuntimeError, match="http://localhost:1234/v1/chat"):
            _raise_on_error(resp, "lm_studio", "http://localhost:1234/v1/chat")

    def test_4xx_raises_with_status_code(self):
        resp = self._make_response(422, "Unprocessable")
        with pytest.raises(RuntimeError, match="422"):
            _raise_on_error(resp, "test", "http://example.com")

    def test_5xx_raises(self):
        resp = self._make_response(500, "Internal Server Error")
        with pytest.raises(RuntimeError, match="500"):
            _raise_on_error(resp, "test", "http://example.com")

    def test_5xx_includes_body(self):
        resp = self._make_response(502, "Bad Gateway")
        with pytest.raises(RuntimeError, match="Bad Gateway"):
            _raise_on_error(resp, "test", "http://example.com")

    def test_long_body_truncated(self):
        long_body = "x" * 1000
        resp = self._make_response(500, long_body)
        with pytest.raises(RuntimeError) as exc_info:
            _raise_on_error(resp, "test", "http://example.com")
        # Body should be truncated to 500 chars
        msg = str(exc_info.value)
        assert "x" * 500 in msg
        assert "x" * 501 not in msg

    def test_200_passes(self):
        resp = self._make_response(200, "OK")
        _raise_on_error(resp, "test", "http://example.com")  # no exception

    def test_body_read_failure_handled(self):
        """When response.text raises, fallback message is used."""
        resp = MagicMock()
        resp.ok = False
        resp.status_code = 500
        type(resp).text = PropertyMock(side_effect=Exception("read error"))
        with pytest.raises(RuntimeError, match="could not read response body"):
            _raise_on_error(resp, "test", "http://example.com")

# ---------------------------------------------------------------------------
# OAI-compat adapter — LM Studio path: allowlist filtering
# ---------------------------------------------------------------------------


class TestLMStudioAllowlistFiltering:
    """LM Studio params are filtered through the lm_studio allowlist."""

    def _lm_studio_provider(self) -> dict:
        """LM Studio provider without lifecycle (allowlist tests only)."""
        return {
            "backend": "lm_studio",
            "adapter": "oai_compat",
            "url": "http://localhost:1234",
            "model": "test-model",
            "timeout": 120,
            "api_key": None,
            "admin_key": None,
            "lifecycle": None,
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
            "lifecycle": {"type": "lm_studio", "ttl": ttl, "context_length": None},
        }

    @staticmethod
    def _mock_model_loaded(model: str = "test-model") -> MagicMock:
        resp = MagicMock()
        resp.ok = True
        resp.json.return_value = {
            "data": [{"id": model, "loaded_instances": [{"config": {}}]}],
        }
        return resp

    def test_lm_studio_ttl_in_payload(
        self, mock_oai_response, monkeypatch
    ):
        """TTL from provider lifecycle is forwarded in payload."""
        gen_payloads: list[dict] = []

        def fake_post(url, **kwargs):
            if "/v1/chat/completions" in url:
                gen_payloads.append(kwargs.get("json", {}))
            return mock_oai_response

        monkeypatch.setattr("adapters.base.requests.post", fake_post)
        monkeypatch.setattr(
            "requests.get", lambda *a, **kw: self._mock_model_loaded(),
        )

        adapter = OAICompatAdapter()
        adapter.generate(
            self._lm_studio_provider(ttl=30),
            [{"role": "user", "content": "hi"}],
            {},
        )

        assert gen_payloads[0]["ttl"] == 30

    def test_lm_studio_ttl_absent_when_none(
        self, mock_oai_response, monkeypatch
    ):
        """TTL omitted from payload when lifecycle has ttl=None."""
        gen_payloads: list[dict] = []

        def fake_post(url, **kwargs):
            if "/v1/chat/completions" in url:
                gen_payloads.append(kwargs.get("json", {}))
            return mock_oai_response

        monkeypatch.setattr("adapters.base.requests.post", fake_post)
        monkeypatch.setattr(
            "requests.get", lambda *a, **kw: self._mock_model_loaded(),
        )

        provider = self._lm_studio_provider()
        provider["lifecycle"]["ttl"] = None
        adapter = OAICompatAdapter()
        adapter.generate(
            provider,
            [{"role": "user", "content": "hi"}],
            {},
        )

        assert "ttl" not in gen_payloads[0]

    def test_lm_studio_mid_chain_ttl_extension(
        self, mock_oai_response, monkeypatch
    ):
        """skip_unload=True extends TTL to max(ttl*10, 300)."""
        gen_payloads: list[dict] = []

        def fake_post(url, **kwargs):
            if "/v1/chat/completions" in url:
                gen_payloads.append(kwargs.get("json", {}))
            return mock_oai_response

        monkeypatch.setattr("adapters.base.requests.post", fake_post)
        monkeypatch.setattr(
            "requests.get", lambda *a, **kw: self._mock_model_loaded(),
        )

        adapter = OAICompatAdapter()
        adapter.generate(
            self._lm_studio_provider(ttl=30),
            [{"role": "user", "content": "hi"}],
            {},
            skip_unload=True,
        )

        # max(30*10, 300) = 300
        assert gen_payloads[0]["ttl"] == 300

    def test_lm_studio_mid_chain_ttl_extension_large_ttl(
        self, mock_oai_response, monkeypatch
    ):
        """When base TTL is large, extended TTL = ttl*10."""
        gen_payloads: list[dict] = []

        def fake_post(url, **kwargs):
            if "/v1/chat/completions" in url:
                gen_payloads.append(kwargs.get("json", {}))
            return mock_oai_response

        monkeypatch.setattr("adapters.base.requests.post", fake_post)
        monkeypatch.setattr(
            "requests.get", lambda *a, **kw: self._mock_model_loaded(),
        )

        adapter = OAICompatAdapter()
        adapter.generate(
            self._lm_studio_provider(ttl=60),
            [{"role": "user", "content": "hi"}],
            {},
            skip_unload=True,
        )

        # max(60*10, 300) = 600
        assert gen_payloads[0]["ttl"] == 600


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
            "lifecycle": None,
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
            "lifecycle": None,
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


# ---------------------------------------------------------------------------
# OAI-compat adapter — text-gen-webui path: allowlist filtering
# ---------------------------------------------------------------------------


class TestTextGenWebuiAllowlistFiltering:
    """text-gen-webui params are filtered through text_gen_webui allowlist."""

    def test_text_gen_webui_allowed_params_forwarded(
        self, text_gen_webui_provider, mock_oai_response, monkeypatch
    ):
        """Params in text_gen_webui allowlist appear in payload."""
        gen_payloads: list[dict] = []

        def fake_post(url, **kwargs):
            if "/v1/chat/completions" in url:
                gen_payloads.append(kwargs.get("json", {}))
            return mock_oai_response

        monkeypatch.setattr("requests.post", fake_post)
        monkeypatch.setattr(
            "requests.get",
            lambda *a, **kw: _model_info_response("my-model"),
        )

        adapter = OAICompatAdapter()
        adapter.generate(
            text_gen_webui_provider,
            [{"role": "user", "content": "hi"}],
            {"temperature": 0.7, "min_p": 0.1, "tfs": 0.9, "typical_p": 0.8},
        )

        payload = gen_payloads[0]
        assert payload["temperature"] == 0.7
        assert payload["min_p"] == 0.1
        assert payload["tfs"] == 0.9
        assert payload["typical_p"] == 0.8

    def test_text_gen_webui_unsupported_param_dropped(
        self, text_gen_webui_provider, mock_oai_response, monkeypatch
    ):
        """Params not in text_gen_webui allowlist are dropped."""
        gen_payloads: list[dict] = []

        def fake_post(url, **kwargs):
            if "/v1/chat/completions" in url:
                gen_payloads.append(kwargs.get("json", {}))
            return mock_oai_response

        monkeypatch.setattr("requests.post", fake_post)
        monkeypatch.setattr(
            "requests.get",
            lambda *a, **kw: _model_info_response("my-model"),
        )

        adapter = OAICompatAdapter()
        adapter.generate(
            text_gen_webui_provider,
            [{"role": "user", "content": "hi"}],
            {"temperature": 0.5, "bogus_param": 42},
        )

        payload = gen_payloads[0]
        assert payload["temperature"] == 0.5
        assert "bogus_param" not in payload

    def test_text_gen_webui_has_params_not_in_lm_studio(self):
        """text_gen_webui allowlist includes min_p, tfs, typical_p."""
        from adapters.oai_compat import BACKEND_ALLOWLISTS

        tgw = BACKEND_ALLOWLISTS["text_gen_webui"]
        lms = BACKEND_ALLOWLISTS["lm_studio"]
        # These are in text_gen_webui but not lm_studio
        assert "min_p" in tgw
        assert "min_p" not in lms
        assert "tfs" in tgw
        assert "tfs" not in lms
        assert "typical_p" in tgw
        assert "typical_p" not in lms


# ---------------------------------------------------------------------------
# OAI-compat adapter — text-gen-webui path: model lifecycle
# ---------------------------------------------------------------------------


def _model_info_response(model_name: str) -> MagicMock:
    """Create a mock GET response for /v1/internal/model/info."""
    resp = MagicMock()
    resp.ok = True
    resp.json.return_value = {"model_name": model_name}
    return resp


class TestTextGenWebuiModelLifecycle:
    """Full lifecycle: check loaded model -> load if needed -> generate -> unload."""

    def test_text_gen_webui_skips_load_when_model_already_loaded(
        self, text_gen_webui_provider, mock_oai_response, monkeypatch
    ):
        """If model is already loaded, no load POST is made."""
        post_urls: list[str] = []

        def fake_post(url, **kwargs):
            post_urls.append(url)
            return mock_oai_response

        monkeypatch.setattr("requests.post", fake_post)
        monkeypatch.setattr(
            "requests.get",
            lambda *a, **kw: _model_info_response("my-model"),
        )

        adapter = OAICompatAdapter()
        adapter.generate(
            text_gen_webui_provider,
            [{"role": "user", "content": "hi"}],
            {},
        )

        # generate POST + unload POST, but no load POST
        load_urls = [u for u in post_urls if "/v1/internal/model/load" in u]
        gen_urls = [u for u in post_urls if "/v1/chat/completions" in u]
        assert len(load_urls) == 0
        assert len(gen_urls) == 1

    def test_text_gen_webui_loads_model_when_different(
        self, text_gen_webui_provider, mock_oai_response, monkeypatch
    ):
        """If a different model is loaded, adapter sends load request."""
        post_urls: list[str] = []

        def fake_post(url, **kwargs):
            post_urls.append(url)
            return mock_oai_response

        monkeypatch.setattr("requests.post", fake_post)
        monkeypatch.setattr(
            "requests.get",
            lambda *a, **kw: _model_info_response("other-model"),
        )

        adapter = OAICompatAdapter()
        adapter.generate(
            text_gen_webui_provider,
            [{"role": "user", "content": "hi"}],
            {},
        )

        load_urls = [u for u in post_urls if "/v1/internal/model/load" in u]
        gen_urls = [u for u in post_urls if "/v1/chat/completions" in u]
        assert len(load_urls) == 1
        assert len(gen_urls) == 1

    def test_text_gen_webui_loads_model_when_info_fails(
        self, text_gen_webui_provider, mock_oai_response, monkeypatch
    ):
        """If model info GET fails, adapter proceeds to load."""
        post_urls: list[str] = []

        def fake_post(url, **kwargs):
            post_urls.append(url)
            return mock_oai_response

        def fake_get_fail(*args, **kwargs):
            raise requests.ConnectionError("offline")

        monkeypatch.setattr("requests.post", fake_post)
        monkeypatch.setattr("requests.get", fake_get_fail)

        adapter = OAICompatAdapter()
        adapter.generate(
            text_gen_webui_provider,
            [{"role": "user", "content": "hi"}],
            {},
        )

        load_urls = [u for u in post_urls if "/v1/internal/model/load" in u]
        assert len(load_urls) == 1

    def test_text_gen_webui_unloads_after_generation(
        self, text_gen_webui_provider, mock_oai_response, monkeypatch
    ):
        """After generation, model is unloaded (last in chain)."""
        post_urls: list[str] = []

        def fake_post(url, **kwargs):
            post_urls.append(url)
            return mock_oai_response

        monkeypatch.setattr("requests.post", fake_post)
        monkeypatch.setattr(
            "requests.get",
            lambda *a, **kw: _model_info_response("my-model"),
        )

        adapter = OAICompatAdapter()
        adapter.generate(
            text_gen_webui_provider,
            [{"role": "user", "content": "hi"}],
            {},
        )

        unload_urls = [u for u in post_urls if "/v1/internal/model/unload" in u]
        assert len(unload_urls) == 1

    def test_text_gen_webui_unload_skipped_mid_chain(
        self, text_gen_webui_provider, mock_oai_response, monkeypatch
    ):
        """When skip_unload=True (mid-chain), unload is not called."""
        post_urls: list[str] = []

        def fake_post(url, **kwargs):
            post_urls.append(url)
            return mock_oai_response

        monkeypatch.setattr("requests.post", fake_post)
        monkeypatch.setattr(
            "requests.get",
            lambda *a, **kw: _model_info_response("my-model"),
        )

        adapter = OAICompatAdapter()
        adapter.generate(
            text_gen_webui_provider,
            [{"role": "user", "content": "hi"}],
            {},
            skip_unload=True,
        )

        unload_urls = [u for u in post_urls if "/v1/internal/model/unload" in u]
        assert len(unload_urls) == 0

    def test_text_gen_webui_load_sends_model_name(
        self, text_gen_webui_provider, mock_oai_response, monkeypatch
    ):
        """Load request includes model_name in JSON body."""
        load_payloads: list[dict] = []

        def fake_post(url, **kwargs):
            if "/v1/internal/model/load" in url:
                load_payloads.append(kwargs.get("json", {}))
            return mock_oai_response

        monkeypatch.setattr("requests.post", fake_post)
        monkeypatch.setattr(
            "requests.get",
            lambda *a, **kw: _model_info_response("other-model"),
        )

        adapter = OAICompatAdapter()
        adapter.generate(
            text_gen_webui_provider,
            [{"role": "user", "content": "hi"}],
            {},
        )

        assert len(load_payloads) == 1
        assert load_payloads[0]["model_name"] == "my-model"

    def test_text_gen_webui_get_info_uses_api_key_load_unload_use_admin(
        self, text_gen_webui_provider, mock_oai_response, monkeypatch
    ):
        """Upstream gates model/info with --api-key and load/unload with --admin-key."""
        get_auth: list[str | None] = []
        post_pairs: list[tuple[str, str | None]] = []

        def fake_get(url, **kwargs):
            get_auth.append((kwargs.get("headers") or {}).get("Authorization"))
            return _model_info_response("other-model")

        def fake_post(url, **kwargs):
            post_pairs.append(
                (url, (kwargs.get("headers") or {}).get("Authorization")),
            )
            return mock_oai_response

        monkeypatch.setattr("requests.get", fake_get)
        monkeypatch.setattr("requests.post", fake_post)

        adapter = OAICompatAdapter()
        adapter.generate(
            text_gen_webui_provider,
            [{"role": "user", "content": "hi"}],
            {},
        )

        assert get_auth == ["Bearer test-api-key"]
        load_auth = [a for u, a in post_pairs if "/v1/internal/model/load" in u]
        unload_auth = [a for u, a in post_pairs if "/v1/internal/model/unload" in u]
        assert load_auth == ["Bearer test-admin-key"]
        assert unload_auth == ["Bearer test-admin-key"]

    def test_text_gen_webui_loads_when_info_model_name_is_none_string(
        self, text_gen_webui_provider, mock_oai_response, monkeypatch
    ):
        """Idle VRAM reports model_name 'None' — treat as unloaded."""
        post_urls: list[str] = []

        def fake_post(url, **kwargs):
            post_urls.append(url)
            return mock_oai_response

        monkeypatch.setattr("requests.post", fake_post)
        monkeypatch.setattr(
            "requests.get",
            lambda *a, **kw: _model_info_response("None"),
        )

        adapter = OAICompatAdapter()
        adapter.generate(
            text_gen_webui_provider,
            [{"role": "user", "content": "hi"}],
            {},
        )

        assert any("/v1/internal/model/load" in u for u in post_urls)


# ---------------------------------------------------------------------------
# OAI-compat adapter — text-gen-webui path: admin key headers
# ---------------------------------------------------------------------------


class TestTextGenWebuiAdminHeaders:
    """Admin key is used for Textgen load/unload; API key for model/info and chat."""

    def test_text_gen_webui_api_key_used_for_model_info(
        self, text_gen_webui_provider, mock_oai_response, monkeypatch
    ):
        """Model info GET uses api_key (Textgen ``check_key``), not admin_key."""
        get_headers: dict = {}

        def fake_get(*args, **kwargs):
            get_headers.update(kwargs.get("headers", {}))
            return _model_info_response("my-model")

        monkeypatch.setattr("requests.post", lambda url, **kw: mock_oai_response)
        monkeypatch.setattr("requests.get", fake_get)

        adapter = OAICompatAdapter()
        adapter.generate(
            text_gen_webui_provider,
            [{"role": "user", "content": "hi"}],
            {},
        )

        assert get_headers["Authorization"] == "Bearer test-api-key"

    def test_text_gen_webui_admin_key_used_for_load(
        self, text_gen_webui_provider, mock_oai_response, monkeypatch
    ):
        """Model load POST uses admin_key."""
        load_headers: list[dict] = []

        def fake_post(url, **kwargs):
            if "/v1/internal/model/load" in url:
                load_headers.append(kwargs.get("headers", {}))
            return mock_oai_response

        monkeypatch.setattr("requests.post", fake_post)
        monkeypatch.setattr(
            "requests.get",
            lambda *a, **kw: _model_info_response("other-model"),
        )

        adapter = OAICompatAdapter()
        adapter.generate(
            text_gen_webui_provider,
            [{"role": "user", "content": "hi"}],
            {},
        )

        assert len(load_headers) == 1
        assert load_headers[0]["Authorization"] == "Bearer test-admin-key"

    def test_text_gen_webui_api_key_in_generate_header(
        self, text_gen_webui_provider, mock_oai_response, monkeypatch
    ):
        """Generate POST uses api_key (not admin_key) for auth."""
        gen_headers: list[dict] = []

        def fake_post(url, **kwargs):
            if "/v1/chat/completions" in url:
                gen_headers.append(kwargs.get("headers", {}))
            return mock_oai_response

        monkeypatch.setattr("requests.post", fake_post)
        monkeypatch.setattr(
            "requests.get",
            lambda *a, **kw: _model_info_response("my-model"),
        )

        adapter = OAICompatAdapter()
        adapter.generate(
            text_gen_webui_provider,
            [{"role": "user", "content": "hi"}],
            {},
        )

        assert len(gen_headers) == 1
        assert gen_headers[0]["Authorization"] == "Bearer test-api-key"

    def test_text_gen_webui_admin_key_used_for_chat_when_no_api_key(
        self, text_gen_webui_provider, mock_oai_response, monkeypatch
    ):
        """Generate POST uses admin_key when api_key is unset (single --api-key)."""
        gen_headers: list[dict] = []

        def fake_post(url, **kwargs):
            if "/v1/chat/completions" in url:
                gen_headers.append(kwargs.get("headers", {}))
            return mock_oai_response

        text_gen_webui_provider["api_key"] = None
        monkeypatch.setattr("requests.post", fake_post)
        monkeypatch.setattr(
            "requests.get",
            lambda *a, **kw: _model_info_response("my-model"),
        )

        adapter = OAICompatAdapter()
        adapter.generate(
            text_gen_webui_provider,
            [{"role": "user", "content": "hi"}],
            {},
        )

        assert len(gen_headers) == 1
        assert gen_headers[0]["Authorization"] == "Bearer test-admin-key"

    def test_text_gen_webui_fallback_to_api_key_when_no_admin_key(
        self, text_gen_webui_provider, mock_oai_response, monkeypatch
    ):
        """When admin_key is None, api_key is used for internal endpoints."""
        get_headers: dict = {}

        def fake_get(*args, **kwargs):
            get_headers.update(kwargs.get("headers", {}))
            return _model_info_response("my-model")

        text_gen_webui_provider["admin_key"] = None
        monkeypatch.setattr("requests.post", lambda url, **kw: mock_oai_response)
        monkeypatch.setattr("requests.get", fake_get)

        adapter = OAICompatAdapter()
        adapter.generate(
            text_gen_webui_provider,
            [{"role": "user", "content": "hi"}],
            {},
        )

        assert get_headers["Authorization"] == "Bearer test-api-key"


# ---------------------------------------------------------------------------
# OAI-compat adapter — text-gen-webui path: unload failure is non-fatal
# ---------------------------------------------------------------------------


class TestTextGenWebuiUnloadFailure:
    """Unload failures are logged as warnings but do not raise."""

    def test_text_gen_webui_unload_connection_error_non_fatal(
        self, text_gen_webui_provider, mock_oai_response, monkeypatch
    ):
        """ConnectionError during unload is caught and logged."""
        call_count = {"n": 0}

        def fake_post(url, **kwargs):
            call_count["n"] += 1
            if "/v1/internal/model/unload" in url:
                raise requests.ConnectionError("refused")
            return mock_oai_response

        monkeypatch.setattr("requests.post", fake_post)
        monkeypatch.setattr(
            "requests.get",
            lambda *a, **kw: _model_info_response("my-model"),
        )

        adapter = OAICompatAdapter()
        result = adapter.generate(
            text_gen_webui_provider,
            [{"role": "user", "content": "hi"}],
            {},
        )
        assert result == "Hello from the model!"

    def test_text_gen_webui_unload_timeout_non_fatal(
        self, text_gen_webui_provider, mock_oai_response, monkeypatch
    ):
        """Timeout during unload is caught and logged."""

        def fake_post(url, **kwargs):
            if "/v1/internal/model/unload" in url:
                raise requests.Timeout("timed out")
            return mock_oai_response

        monkeypatch.setattr("requests.post", fake_post)
        monkeypatch.setattr(
            "requests.get",
            lambda *a, **kw: _model_info_response("my-model"),
        )

        adapter = OAICompatAdapter()
        result = adapter.generate(
            text_gen_webui_provider,
            [{"role": "user", "content": "hi"}],
            {},
        )
        assert result == "Hello from the model!"

    def test_text_gen_webui_unload_generic_request_error_non_fatal(
        self, text_gen_webui_provider, mock_oai_response, monkeypatch
    ):
        """Generic RequestException during unload is caught and logged."""

        def fake_post(url, **kwargs):
            if "/v1/internal/model/unload" in url:
                raise requests.RequestException("something failed")
            return mock_oai_response

        monkeypatch.setattr("requests.post", fake_post)
        monkeypatch.setattr(
            "requests.get",
            lambda *a, **kw: _model_info_response("my-model"),
        )

        adapter = OAICompatAdapter()
        result = adapter.generate(
            text_gen_webui_provider,
            [{"role": "user", "content": "hi"}],
            {},
        )
        assert result == "Hello from the model!"
