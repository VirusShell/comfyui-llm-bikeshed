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
        seed: int = -1,
    ) -> dict:
        """Helper: call generate() with a mock adapter and return the options dict."""
        node = LLMGenerate()
        mock_adapter = MagicMock()
        mock_adapter.generate.return_value = "response text"
        provider = {"adapter": "oai_compat", "url": "http://localhost:1234"}

        with patch("nodes.generation.get_adapter", return_value=mock_adapter), \
             patch("nodes.generation.has_downstream_gen_node", return_value=False):
            node.generate(
                provider=provider,
                prompt="Hello",
                system_prompt="",
                temperature=temperature,
                max_tokens=max_tokens,
                seed=seed,
            )

        # Third positional arg to adapter.generate is the options dict
        call_args = mock_adapter.generate.call_args
        return call_args[0][2]

    def test_seed_negative_one_excluded(self) -> None:
        opts = self._run_generate(seed=-1)
        assert "seed" not in opts

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

    def test_all_defaults_no_seed(self) -> None:
        """Default seed=-1 excluded, but temperature and max_tokens included."""
        opts = self._run_generate()
        assert "seed" not in opts
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
                provider=provider,
                options=explicit_opts,
                meta=meta_input,
            )

        call_options = mock_adapter.generate.call_args[0][2]
        assert call_options["temperature"] == 0.9
        assert call_options["max_tokens"] == 2048
        assert meta_out["options"] == explicit_opts

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
                system_prompt="", prompt="Hello", provider=None, meta=None,
            )
            assert False, "Expected ValueError"
        except ValueError as exc:
            assert "No provider configured" in str(exc)
