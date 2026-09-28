"""Tests for generation node message building and inline options."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from nodes.generation import LLMGenerate, LLMGenerateAdvanced, _build_messages

# ---------------------------------------------------------------------------
# _build_messages
# ---------------------------------------------------------------------------


class TestBuildMessages:
    """Message list construction from system/user prompts."""

    def test_with_system_prompt(self) -> None:
        msgs = _build_messages("You are helpful.", "Hello")
        assert msgs == [
            {"role": "system", "content": "You are helpful."},
            {"role": "user", "content": "Hello"},
        ]

    def test_without_system_prompt(self) -> None:
        msgs = _build_messages("", "Hello")
        assert msgs == [{"role": "user", "content": "Hello"}]

    def test_whitespace_system_prompt_excluded(self) -> None:
        """Empty string is falsy, so no system message."""
        msgs = _build_messages("", "What time is it?")
        assert len(msgs) == 1
        assert msgs[0]["role"] == "user"

    def test_user_prompt_always_present(self) -> None:
        msgs = _build_messages("sys", "usr")
        roles = [m["role"] for m in msgs]
        assert "user" in roles


# ---------------------------------------------------------------------------
# LLMGenerate — inline option sentinel exclusion
# ---------------------------------------------------------------------------


class TestLLMGenerateInlineOptions:
    """Sentinel values are excluded from options dict passed to adapter."""

    def _run_generate(
        self,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        seed: int = 0,
        backend: str | None = None,
        extra_pnginfo: object = None,
        unique_id: object = None,
    ) -> dict:
        """Helper: call generate() with a mock adapter and return the options dict."""
        node = LLMGenerate()
        mock_adapter = MagicMock()
        mock_adapter.generate.return_value = "response text"
        provider = {"adapter": "oai_compat", "url": "http://localhost:1234"}
        if backend is not None:
            provider["backend"] = backend

        with patch("nodes.generation.get_adapter", return_value=mock_adapter), \
             patch("nodes.generation.has_downstream_gen_node", return_value=False):
            node.generate(
                provider=provider,
                prompt="Hello",
                system_prompt="",
                temperature=temperature,
                max_tokens=max_tokens,
                seed=seed,
                extra_pnginfo=extra_pnginfo,
                unique_id=unique_id,
            )

        # Third positional arg to adapter.generate is the options dict
        call_args = mock_adapter.generate.call_args
        self.last_call = call_args
        return call_args[0][2]

    def test_seed_zero_included(self) -> None:
        opts = self._run_generate(seed=0)
        assert opts["seed"] == 0

    def test_seed_positive_included(self) -> None:
        opts = self._run_generate(seed=42)
        assert opts["seed"] == 42

    def test_temperature_included(self) -> None:
        opts = self._run_generate(temperature=0.7)
        assert opts["temperature"] == 0.7

    def test_temperature_zero_included(self) -> None:
        """temperature=0.0 is valid (greedy), should be included."""
        opts = self._run_generate(temperature=0.0)
        assert opts["temperature"] == 0.0

    def test_max_tokens_included(self) -> None:
        opts = self._run_generate(max_tokens=512)
        assert opts["max_tokens"] == 512

    def test_max_tokens_zero_omits_face_limit(self) -> None:
        """0 means omit / host default, not a request for zero tokens."""
        opts = self._run_generate(max_tokens=0)
        assert "max_tokens" not in opts
        assert "max_completion_tokens" not in opts
        assert opts["seed"] == 0

    def test_openai_face_sends_max_completion_tokens(self) -> None:
        opts = self._run_generate(max_tokens=64, backend="openai")
        assert opts["max_completion_tokens"] == 64
        assert "max_tokens" not in opts

    def test_legacy_host_keeps_max_tokens(self) -> None:
        opts = self._run_generate(max_tokens=64, backend="llamacpp")
        assert opts["max_tokens"] == 64
        assert "max_completion_tokens" not in opts

    def test_all_defaults_includes_seed(self) -> None:
        """Comfy-style seed default 0 is always sent with temperature/max_tokens."""
        opts = self._run_generate()
        assert opts["seed"] == 0
        assert "temperature" in opts
        assert "max_tokens" in opts


# ---------------------------------------------------------------------------
# LLMGenerateAdvanced — meta precedence
# ---------------------------------------------------------------------------


class TestLLMGenerateAdvancedMetaPrecedence:
    """Explicit provider/options inputs win over meta values."""

    def _make_provider(self, name: str) -> dict:
        return {"adapter": "oai_compat", "url": f"http://{name}:1234"}

    def test_explicit_provider_wins_over_meta(self) -> None:
        node = LLMGenerateAdvanced()
        explicit_prov = self._make_provider("explicit")
        meta_prov = self._make_provider("meta")
        meta_input = {"provider": meta_prov, "options": {}}

        mock_adapter = MagicMock()
        mock_adapter.generate.return_value = "text"

        with patch("nodes.generation.get_adapter", return_value=mock_adapter), \
             patch("nodes.generation.has_downstream_gen_node", return_value=False):
            text, meta_out = node.generate(
                system_prompt="",
                prompt="Hello",
                seed=0,
                provider=explicit_prov,
                meta=meta_input,
            )

        # Provider passed to adapter should be the explicit one
        call_provider = mock_adapter.generate.call_args[0][0]
        assert call_provider["url"] == "http://explicit:1234"
        assert meta_out["provider"]["url"] == "http://explicit:1234"

    def test_meta_provider_used_when_no_explicit(self) -> None:
        node = LLMGenerateAdvanced()
        meta_prov = self._make_provider("meta")
        meta_input = {"provider": meta_prov, "options": {"temperature": 0.5}}

        mock_adapter = MagicMock()
        mock_adapter.generate.return_value = "text"

        with patch("nodes.generation.get_adapter", return_value=mock_adapter), \
             patch("nodes.generation.has_downstream_gen_node", return_value=False):
            text, meta_out = node.generate(
                system_prompt="",
                prompt="Hello",
                seed=0,
                provider=None,
                meta=meta_input,
            )

        call_provider = mock_adapter.generate.call_args[0][0]
        assert call_provider["url"] == "http://meta:1234"

    def test_explicit_options_wins_over_meta(self) -> None:
        node = LLMGenerateAdvanced()
        provider = self._make_provider("host")
        explicit_opts = {"temperature": 0.9, "max_tokens": 2048}
        meta_opts = {"temperature": 0.1, "max_tokens": 100}
        meta_input = {"provider": provider, "options": meta_opts}

        mock_adapter = MagicMock()
        mock_adapter.generate.return_value = "text"

        with patch("nodes.generation.get_adapter", return_value=mock_adapter), \
             patch("nodes.generation.has_downstream_gen_node", return_value=False):
            text, meta_out = node.generate(
                system_prompt="",
                prompt="Hello",
                seed=0,
                provider=provider,
                options=explicit_opts,
                meta=meta_input,
            )

        call_options = mock_adapter.generate.call_args[0][2]
        assert call_options["temperature"] == 0.9
        assert call_options["max_tokens"] == 2048
        assert call_options["seed"] == 0
        assert meta_out["options"]["temperature"] == 0.9
        assert meta_out["options"]["max_tokens"] == 2048
        assert meta_out["options"]["seed"] == 0

    def test_meta_options_used_when_no_explicit(self) -> None:
        node = LLMGenerateAdvanced()
        provider = self._make_provider("host")
        meta_opts = {"temperature": 0.3}
        meta_input = {"provider": provider, "options": meta_opts}

        mock_adapter = MagicMock()
        mock_adapter.generate.return_value = "text"

        with patch("nodes.generation.get_adapter", return_value=mock_adapter), \
             patch("nodes.generation.has_downstream_gen_node", return_value=False):
            text, meta_out = node.generate(
                system_prompt="",
                prompt="Hello",
                seed=0,
                provider=provider,
                options=None,
                meta=meta_input,
            )

        call_options = mock_adapter.generate.call_args[0][2]
        assert call_options["temperature"] == 0.3

    def test_no_provider_no_meta_raises(self) -> None:
        node = LLMGenerateAdvanced()
        try:
            node.generate(
                system_prompt="",
                prompt="Hello",
                seed=0,
                provider=None,
                meta=None,
            )
            assert False, "Expected ValueError"
        except ValueError as exc:
            assert "No provider configured" in str(exc)




# ---------------------------------------------------------------------------
# LLMGenerateAdvanced - seed widget
# ---------------------------------------------------------------------------


class TestLLMGenerateAdvancedSeed:
    """Node seed widget always merges into options (Comfy-style seed)."""

    def _make_provider(self) -> dict:
        return {"adapter": "oai_compat", "url": "http://host:1234"}

    def _run(
        self,
        seed: int,
        options: dict | None = None,
        meta: dict | None = None,
    ) -> dict:
        node = LLMGenerateAdvanced()
        mock_adapter = MagicMock()
        mock_adapter.generate.return_value = "text"
        provider = self._make_provider()
        with patch("nodes.generation.get_adapter", return_value=mock_adapter), \
             patch("nodes.generation.has_downstream_gen_node", return_value=False):
            node.generate(
                system_prompt="",
                prompt="Hello",
                seed=seed,
                provider=provider,
                options=options,
                meta=meta,
            )
        return mock_adapter.generate.call_args[0][2]

    def test_seed_positive_sets_options(self) -> None:
        opts = self._run(seed=42, options={"temperature": 0.5})
        assert opts["seed"] == 42
        assert opts["temperature"] == 0.5

    def test_seed_positive_overrides_options_seed(self) -> None:
        opts = self._run(seed=99, options={"seed": 1})
        assert opts["seed"] == 99

    def test_seed_zero_overrides_options_seed(self) -> None:
        opts = self._run(seed=0, options={"seed": 7})
        assert opts["seed"] == 0

    def test_seed_always_present_even_without_options_seed(self) -> None:
        opts = self._run(seed=0, options={"temperature": 0.2})
        assert opts["seed"] == 0

    def test_seed_does_not_mutate_input_options_dict(self) -> None:
        original = {"temperature": 0.5}
        self._run(seed=42, options=original)
        assert "seed" not in original


class TestMetaSecretStripping:
    """LLM_META outputs must not carry api_key or admin_key."""

    def test_basic_generate_strips_secrets_from_meta(self) -> None:
        node = LLMGenerate()
        provider = {
            "adapter": "oai_compat",
            "url": "http://localhost:1234",
            "api_key": "leaked",
            "admin_key": "also-leaked",
        }
        mock_adapter = MagicMock()
        mock_adapter.generate.return_value = "text"

        with patch("nodes.generation.get_adapter", return_value=mock_adapter), \
             patch("nodes.generation.has_downstream_gen_node", return_value=False):
            _, meta = node.generate(
                provider=provider,
                prompt="Hello",
                system_prompt="",
                temperature=0.7,
                max_tokens=1024,
                seed=0,
            )

        assert "api_key" not in meta["provider"]
        assert "admin_key" not in meta["provider"]


class TestGenerateFaceShape:
    """Q4: Advanced-shaped spine, max_tokens above seed, min 0. Both stay registered."""

    def test_basic_max_tokens_above_seed_min_zero(self) -> None:
        required = LLMGenerate.INPUT_TYPES()["required"]
        keys = list(required)
        assert keys.index("max_tokens") < keys.index("seed")
        assert required["max_tokens"][1]["min"] == 0
        assert required["max_tokens"][1]["default"] == 1024

    def test_advanced_keeps_optional_sockets_and_token_knob(self) -> None:
        required = LLMGenerateAdvanced.INPUT_TYPES()["required"]
        optional = LLMGenerateAdvanced.INPUT_TYPES()["optional"]
        keys = list(required)
        assert keys.index("max_tokens") < keys.index("seed")
        assert required["max_tokens"][1]["min"] == 0
        assert "temperature" not in required
        assert set(optional) == {"provider", "options", "meta"}


class TestAdvancedFaceMaxTokens:
    """Face >= 1 wins. Face 0 leaves Options / meta token limits in place."""

    def _provider(self, backend: str = "lm_studio") -> dict:
        return {
            "adapter": "oai_compat",
            "url": "http://host:1234",
            "backend": backend,
        }

    def _opts(self, **kwargs: object) -> dict:
        node = LLMGenerateAdvanced()
        mock_adapter = MagicMock()
        mock_adapter.generate.return_value = "text"
        provider = kwargs.pop("provider", self._provider())
        with patch("nodes.generation.get_adapter", return_value=mock_adapter), \
             patch("nodes.generation.has_downstream_gen_node", return_value=False):
            node.generate(system_prompt="", prompt="Hello", provider=provider, **kwargs)
        self.call = mock_adapter.generate.call_args
        return self.call[0][2]

    def test_zero_keeps_options_max_tokens(self) -> None:
        opts = self._opts(max_tokens=0, options={"max_tokens": 50, "temperature": 0.2})
        assert opts["max_tokens"] == 50
        assert opts["temperature"] == 0.2

    def test_positive_overrides_options_on_legacy_host(self) -> None:
        opts = self._opts(max_tokens=80, options={"max_tokens": 50})
        assert opts["max_tokens"] == 80

    def test_positive_openai_uses_completion_tokens(self) -> None:
        opts = self._opts(
            max_tokens=80,
            options={"max_tokens": 50, "temperature": 0.4},
            provider=self._provider("openai"),
        )
        assert opts["max_completion_tokens"] == 80
        assert "max_tokens" not in opts
        assert opts["temperature"] == 0.4
        assert opts["seed"] == 0


class TestUnloadOnInterruptProperty:
    """Q5: property is not a face widget; missing workflow blob stays off."""

    def test_property_not_a_required_widget(self) -> None:
        for cls in (LLMGenerate, LLMGenerateAdvanced):
            types = cls.INPUT_TYPES()
            assert "unload_on_interrupt" not in types["required"]
            assert "unload_on_interrupt" not in types.get("optional", {})

    def test_basic_passes_flag_from_workflow_properties(self) -> None:
        node = LLMGenerate()
        mock_adapter = MagicMock()
        mock_adapter.generate.return_value = "text"
        extra = {
            "workflow": {
                "nodes": [
                    {
                        "id": 7,
                        "properties": {"unload_on_interrupt": True},
                    }
                ]
            }
        }
        with patch("nodes.generation.get_adapter", return_value=mock_adapter), \
             patch("nodes.generation.has_downstream_gen_node", return_value=False):
            node.generate(
                provider={"adapter": "oai_compat", "url": "http://localhost"},
                prompt="Hello",
                system_prompt="",
                temperature=0.7,
                max_tokens=16,
                seed=1,
                unique_id=7,
                extra_pnginfo=extra,
            )
        assert mock_adapter.generate.call_args.kwargs["unload_on_interrupt"] is True

    def test_missing_workflow_defaults_off(self) -> None:
        node = LLMGenerateAdvanced()
        mock_adapter = MagicMock()
        mock_adapter.generate.return_value = "text"
        provider = {
            "adapter": "oai_compat",
            "url": "http://localhost",
            "backend": "lm_studio",
        }
        with patch("nodes.generation.get_adapter", return_value=mock_adapter), \
             patch("nodes.generation.has_downstream_gen_node", return_value=False):
            node.generate(
                system_prompt="",
                prompt="Hello",
                max_tokens=0,
                seed=0,
                provider=provider,
            )
        assert mock_adapter.generate.call_args.kwargs["unload_on_interrupt"] is False
