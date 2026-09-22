"""Tests for LLM provider nodes."""

from __future__ import annotations

from unittest.mock import patch

from nodes.providers import (
    LLMConnection,
    LLMProviderOAICompat,
    LLMProviderTextGenWebUI,
    resolve_connection_backends,
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
        assert p["load_before_generate"] is True

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
        assert p["load_before_generate"] is False

    def test_validate_rejects_placeholder_model(self) -> None:
        msg = LLMProviderTextGenWebUI.VALIDATE_INPUTS(
            model="(refresh to load)",
            model_fallback="",
        )
        assert isinstance(msg, str)
        assert "Select a model" in msg

    def test_validate_accepts_real_model(self) -> None:
        assert LLMProviderTextGenWebUI.VALIDATE_INPUTS(model="m.gguf") is True

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
            with patch.object(
                providers_mod, "resolve_provider_auth",
                return_value=(None, None),
            ):
                with patch.object(providers_mod, "get_config", return_value={}):
                    node.build_provider("http://h:5000", "m", "", None)
                    node.build_provider("http://h:5000", "m", "", None)
        hits = [
            r for r in caplog.records
            if "LLM Provider: Textgen" in r.getMessage()
        ]
        assert len(hits) == 1

    def test_oai_compat_textgen_auto_load_flag(self) -> None:
        from nodes import providers as providers_mod

        node = LLMProviderOAICompat()
        with patch.object(
            providers_mod, "detect_backend", return_value="text_gen_webui"
        ):
            with patch.object(
                providers_mod, "resolve_provider_auth",
                return_value=(None, None),
            ):
                with patch.object(providers_mod, "get_config", return_value={}):
                    (p,) = node.build_provider(
                        "http://h:5000", "m.gguf", "", None,
                    )
        assert p["load_before_generate"] is True


class TestResolveConnectionBackends:
    def test_override_beats_detect(self) -> None:
        from nodes import providers as providers_mod

        with patch.object(
            providers_mod, "detect_backend", return_value="text_gen_webui",
        ):
            with patch.object(
                providers_mod, "resolve_provider_auth",
                return_value=(None, None),
            ):
                detected, effective, face = resolve_connection_backends(
                    "http://localhost:5000", "LM Studio",
                )
        assert detected == "text_gen_webui"
        assert effective == "lm_studio"
        assert face == "lm_studio"

    def test_auto_ollama_uses_generic_face(self) -> None:
        from nodes import providers as providers_mod

        with patch.object(providers_mod, "detect_backend", return_value="ollama"):
            with patch.object(
                providers_mod, "resolve_provider_auth",
                return_value=(None, None),
            ):
                detected, effective, face = resolve_connection_backends(
                    "http://localhost:11434", "Auto (detect)",
                )
        assert detected == "ollama"
        assert effective == "generic"
        assert face == "generic"


class TestLLMConnection:
    def test_textgen_lifecycle_embedded(self) -> None:
        from nodes import providers as providers_mod

        node = LLMConnection()
        with patch.object(
            providers_mod, "detect_backend", return_value="lm_studio",
        ):
            with patch.object(
                providers_mod, "resolve_provider_auth",
                return_value=(None, None),
            ):
                with patch.object(providers_mod, "get_config", return_value={}):
                    (p,) = node.build_provider(
                        url="http://localhost:5000/",
                        host_mode="Textgen",
                        model="m.gguf",
                        manage_model_memory=True,
                    )
        assert p["backend"] == "text_gen_webui"
        assert p["url"] == "http://localhost:5000"
        assert p["lifecycle"] == {"type": "text_gen_webui"}
        assert p["load_before_generate"] is True
        assert "api_key" not in p

    def test_textgen_manage_memory_off(self) -> None:
        from nodes import providers as providers_mod

        node = LLMConnection()
        with patch.object(
            providers_mod, "detect_backend", return_value="text_gen_webui",
        ):
            with patch.object(
                providers_mod, "resolve_provider_auth",
                return_value=(None, None),
            ):
                with patch.object(providers_mod, "get_config", return_value={}):
                    (p,) = node.build_provider(
                        url="http://localhost:5000",
                        host_mode="Textgen",
                        model="m.gguf",
                        manage_model_memory=False,
                    )
        assert p["lifecycle"] is None
        assert p["load_before_generate"] is False

    def test_lm_studio_lifecycle_embedded(self) -> None:
        from nodes import providers as providers_mod

        node = LLMConnection()
        with patch.object(
            providers_mod, "detect_backend", return_value="generic",
        ):
            with patch.object(
                providers_mod, "resolve_provider_auth",
                return_value=(None, None),
            ):
                with patch.object(providers_mod, "get_config", return_value={}):
                    (p,) = node.build_provider(
                        url="http://localhost:1234",
                        host_mode="LM Studio",
                        model="foo",
                        ttl=45,
                        context_length=4096,
                        manage_model_memory=True,  # ignored off-mode
                    )
        assert p["backend"] == "lm_studio"
        assert p["lifecycle"] == {
            "type": "lm_studio",
            "ttl": 45,
            "context_length": 4096,
        }
        assert p["load_before_generate"] is False

    def test_llamacpp_no_lifecycle(self) -> None:
        from nodes import providers as providers_mod

        node = LLMConnection()
        with patch.object(
            providers_mod, "detect_backend", return_value="llamacpp",
        ):
            with patch.object(
                providers_mod, "resolve_provider_auth",
                return_value=(None, None),
            ):
                with patch.object(providers_mod, "get_config", return_value={}):
                    (p,) = node.build_provider(
                        url="http://localhost:8080",
                        host_mode="llama.cpp",
                        model="id",
                        manage_model_memory=True,
                        ttl=99,
                        context_length=2048,
                    )
        assert p["backend"] == "llamacpp"
        assert p["lifecycle"] is None
        assert p["load_before_generate"] is False

    def test_generic_no_lifecycle(self) -> None:
        from nodes import providers as providers_mod

        node = LLMConnection()
        with patch.object(
            providers_mod, "detect_backend", return_value="generic",
        ):
            with patch.object(
                providers_mod, "resolve_provider_auth",
                return_value=(None, None),
            ):
                with patch.object(providers_mod, "get_config", return_value={}):
                    (p,) = node.build_provider(
                        url="http://localhost:9000",
                        host_mode="Generic OAI",
                        model="x",
                    )
        assert p["backend"] == "generic"
        assert p["lifecycle"] is None

    def test_timeout_zero_uses_config_default(self) -> None:
        from nodes import providers as providers_mod

        node = LLMConnection()
        with patch.object(
            providers_mod, "detect_backend", return_value="openai",
        ):
            with patch.object(
                providers_mod, "resolve_provider_auth",
                return_value=(None, None),
            ):
                with patch.object(providers_mod, "get_config", return_value={}):
                    (p,) = node.build_provider(
                        url="https://api.openai.com",
                        host_mode="OpenAI / OAI-compat",
                        model="gpt-4o-mini",
                        timeout=0,
                    )
        assert p["timeout"] == 120

    def test_timeout_override(self) -> None:
        from nodes import providers as providers_mod

        node = LLMConnection()
        with patch.object(
            providers_mod, "detect_backend", return_value="openai",
        ):
            with patch.object(
                providers_mod, "resolve_provider_auth",
                return_value=(None, None),
            ):
                with patch.object(providers_mod, "get_config", return_value={}):
                    (p,) = node.build_provider(
                        url="https://api.openai.com",
                        host_mode="OpenAI / OAI-compat",
                        model="gpt-4o-mini",
                        timeout=60,
                    )
        assert p["timeout"] == 60

    def test_model_fallback_wins(self) -> None:
        from nodes import providers as providers_mod

        node = LLMConnection()
        with patch.object(
            providers_mod, "detect_backend", return_value="generic",
        ):
            with patch.object(
                providers_mod, "resolve_provider_auth",
                return_value=(None, None),
            ):
                with patch.object(providers_mod, "get_config", return_value={}):
                    (p,) = node.build_provider(
                        url="http://localhost:1",
                        host_mode="Generic OAI",
                        model="(refresh to load)",
                        model_fallback="  typed-id  ",
                    )
        assert p["model"] == "typed-id"

    def test_validate_rejects_placeholder(self) -> None:
        msg = LLMConnection.VALIDATE_INPUTS(
            model="(refresh to load)", model_fallback="",
        )
        assert isinstance(msg, str)

    def test_validate_accepts_string_model(self) -> None:
        assert LLMConnection.VALIDATE_INPUTS(model="any-id") is True

    def test_class_id_unchanged_old_providers(self) -> None:
        assert LLMProviderOAICompat.__name__ == "LLMProviderOAICompat"
        assert LLMProviderTextGenWebUI.__name__ == "LLMProviderTextGenWebUI"
        assert LLMConnection.__name__ == "LLMConnection"

