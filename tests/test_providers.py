"""Tests for LLM provider nodes."""

from __future__ import annotations

from unittest.mock import patch

from nodes.providers import (
    LLMProviderOAICompat,
    LLMProviderTextGenWebUI,
)


class TestLLMProviderTextGenWebUI:
    def test_build_provider_lifecycle_on_url_normalized(self) -> None:
        node = LLMProviderTextGenWebUI()
        with patch("nodes.providers.get_config", return_value={}):
            (p,) = node.build_provider(
                "http://localhost:5000/",
                "m.gguf",
                True,
                "",
            )
        assert p["backend"] == "text_gen_webui"
        assert p["adapter"] == "oai_compat"
        assert p["url"] == "http://localhost:5000"
        assert p["model"] == "m.gguf"
        assert p["timeout"] == 120
        assert "api_key" not in p
        assert "admin_key" not in p
        assert p["lifecycle"] == {"type": "text_gen_webui"}

    def test_build_provider_lifecycle_off(self) -> None:
        node = LLMProviderTextGenWebUI()
        with patch("nodes.providers.get_config", return_value={}):
            (p,) = node.build_provider(
                "http://127.0.0.1:5000",
                "x",
                False,
                "",
            )
        assert p["lifecycle"] is None

    def test_model_fallback_overrides_combo(self) -> None:
        node = LLMProviderTextGenWebUI()
        with patch("nodes.providers.get_config", return_value={}):
            (p,) = node.build_provider(
                "http://127.0.0.1:5000",
                "(refresh to load)",
                True,
                "  remote-id  ",
            )
        assert p["model"] == "remote-id"


class TestLLMProviderOAICompatTextgenHint:
    def test_logs_once_when_backend_is_textgen(self, caplog) -> None:
        import logging

        from nodes import providers as providers_mod

        caplog.set_level(logging.INFO, logger="llm-bikeshed")
        providers_mod._OAI_COMPAT_TEXTGEN_HINT_LOGGED = False
        node = LLMProviderOAICompat()
        with patch.object(
            providers_mod, "detect_backend", return_value="text_gen_webui",
        ):
            with patch.object(providers_mod, "get_api_key", return_value=None):
                with patch.object(providers_mod, "get_config", return_value={}):
                    node.build_provider("http://h:5000", "m", "", None)
                    node.build_provider("http://h:5000", "m", "", None)
        hits = [
            r for r in caplog.records
            if "LLM Provider: Textgen" in r.getMessage()
        ]
        assert len(hits) == 1
