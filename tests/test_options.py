"""Tests for Ollama Core Options node (sentinel pattern)."""

from __future__ import annotations

from nodes.options_lm_studio import LLMOptionsLMStudio
from nodes.options_ollama import LLMOptionsOllamaCore, LLMOptionsOllamaExtra
from nodes.options_text_gen_webui import LLMOptionsTextGenWebUI

# ---------------------------------------------------------------------------
# Sentinel exclusion
# ---------------------------------------------------------------------------


class TestOllamaCoreOptionsSentinel:
    """Sentinel values (-1 for ints, -1.0 for floats, '' for strings) are excluded."""

    def test_all_sentinels_produce_empty_dict(self) -> None:
        node = LLMOptionsOllamaCore()
        (result,) = node.build_options(
            temperature=-1.0,
            top_k=-1,
            top_p=-1.0,
            seed=-1,
            num_predict=-1,
            num_ctx=-1,
            stop="",
        )
        assert result == {}

    def test_float_sentinel_excluded(self) -> None:
        node = LLMOptionsOllamaCore()
        (result,) = node.build_options(temperature=-1.0, top_p=-1.0)
        assert "temperature" not in result
        assert "top_p" not in result

    def test_int_sentinel_excluded(self) -> None:
        node = LLMOptionsOllamaCore()
        (result,) = node.build_options(top_k=-1, seed=-1, num_predict=-1, num_ctx=-1)
        assert result == {}

    def test_string_sentinel_excluded(self) -> None:
        node = LLMOptionsOllamaCore()
        (result,) = node.build_options(stop="")
        assert "stop" not in result


# ---------------------------------------------------------------------------
# Non-sentinel inclusion
# ---------------------------------------------------------------------------


class TestOllamaCoreOptionsNonSentinel:
    """Non-sentinel values are included in the output dict."""

    def test_non_sentinel_float_included(self) -> None:
        node = LLMOptionsOllamaCore()
        (result,) = node.build_options(temperature=0.7, top_p=0.9)
        assert result["temperature"] == 0.7
        assert result["top_p"] == 0.9

    def test_non_sentinel_int_included(self) -> None:
        node = LLMOptionsOllamaCore()
        (result,) = node.build_options(
            top_k=40, seed=42, num_predict=1024, num_ctx=4096,
        )
        assert result == {
            "top_k": 40,
            "seed": 42,
            "num_predict": 1024,
            "num_ctx": 4096,
        }

    def test_non_sentinel_string_included(self) -> None:
        node = LLMOptionsOllamaCore()
        (result,) = node.build_options(stop="<|end|>")
        assert result["stop"] == "<|end|>"

    def test_zero_is_not_sentinel_for_ints(self) -> None:
        """0 != -1, so zero should be included."""
        node = LLMOptionsOllamaCore()
        (result,) = node.build_options(top_k=0, seed=0)
        assert result["top_k"] == 0
        assert result["seed"] == 0

    def test_zero_float_is_not_sentinel(self) -> None:
        """0.0 != -1.0, so zero should be included."""
        node = LLMOptionsOllamaCore()
        (result,) = node.build_options(temperature=0.0, top_p=0.0)
        assert result["temperature"] == 0.0
        assert result["top_p"] == 0.0

    def test_mixed_sentinel_and_non_sentinel(self) -> None:
        node = LLMOptionsOllamaCore()
        (result,) = node.build_options(
            temperature=0.5,
            top_k=-1,
            top_p=-1.0,
            seed=42,
            num_predict=-1,
            num_ctx=2048,
            stop="",
        )
        assert result == {"temperature": 0.5, "seed": 42, "num_ctx": 2048}


# ---------------------------------------------------------------------------
# Chaining via options_in
# ---------------------------------------------------------------------------


class TestOllamaCoreOptionsChaining:
    """options_in merges upstream options; Core values override on collision."""

    def test_options_in_keys_passed_through(self) -> None:
        node = LLMOptionsOllamaCore()
        upstream = {"repeat_penalty": 1.2, "mirostat": 1}
        (result,) = node.build_options(
            options_in=upstream,
            temperature=-1.0,
            top_k=-1,
            top_p=-1.0,
            seed=-1,
            num_predict=-1,
            num_ctx=-1,
            stop="",
        )
        assert result["repeat_penalty"] == 1.2
        assert result["mirostat"] == 1

    def test_options_in_does_not_mutate_original(self) -> None:
        node = LLMOptionsOllamaCore()
        upstream = {"repeat_penalty": 1.2}
        node.build_options(options_in=upstream, temperature=0.5)
        assert "temperature" not in upstream

    def test_core_wins_on_collision(self) -> None:
        """When options_in has a key that Core also sets, Core's value wins."""
        node = LLMOptionsOllamaCore()
        upstream = {"temperature": 0.3, "top_k": 10, "extra_param": "keep"}
        (result,) = node.build_options(
            options_in=upstream,
            temperature=0.8,
            top_k=50,
            top_p=-1.0,
            seed=-1,
            num_predict=-1,
            num_ctx=-1,
            stop="",
        )
        assert result["temperature"] == 0.8
        assert result["top_k"] == 50
        assert result["extra_param"] == "keep"

    def test_sentinel_does_not_overwrite_upstream(self) -> None:
        """Sentinel value should NOT remove an upstream key — sentinels are skipped."""
        node = LLMOptionsOllamaCore()
        upstream = {"temperature": 0.5}
        (result,) = node.build_options(
            options_in=upstream,
            temperature=-1.0,
        )
        assert result["temperature"] == 0.5

    def test_no_options_in_defaults_to_empty(self) -> None:
        node = LLMOptionsOllamaCore()
        (result,) = node.build_options(temperature=0.7)
        assert result == {"temperature": 0.7}


# ===========================================================================
# Ollama Extra Options (toggle pattern)
# ===========================================================================

class TestOllamaExtraToggle:
    """Toggle ON includes param, toggle OFF excludes it."""

    def test_all_toggles_off_produces_empty(self) -> None:
        node = LLMOptionsOllamaExtra()
        kwargs = {f"enable_{n}": False for n, _, _ in node.PARAMS}
        kwargs.update({n: opts["default"] for n, _, opts in node.PARAMS})
        (result,) = node.build_options(**kwargs)
        assert result == {}

    def test_toggle_on_includes_param(self) -> None:
        node = LLMOptionsOllamaExtra()
        (result,) = node.build_options(
            enable_repeat_penalty=True, repeat_penalty=1.3,
            enable_mirostat=False, mirostat=0,
        )
        assert result == {"repeat_penalty": 1.3}
        assert "mirostat" not in result

    def test_toggle_off_excludes_even_nondefault(self) -> None:
        node = LLMOptionsOllamaExtra()
        (result,) = node.build_options(
            enable_min_p=False, min_p=0.5,
        )
        assert "min_p" not in result

    def test_mirostat_combo_values(self) -> None:
        node = LLMOptionsOllamaExtra()
        for val in (0, 1, 2):
            (result,) = node.build_options(enable_mirostat=True, mirostat=val)
            assert result["mirostat"] == val

    def test_multiple_toggles_on(self) -> None:
        node = LLMOptionsOllamaExtra()
        (result,) = node.build_options(
            enable_mirostat=True, mirostat=2,
            enable_mirostat_eta=True, mirostat_eta=0.2,
            enable_mirostat_tau=True, mirostat_tau=3.0,
            enable_repeat_penalty=False, repeat_penalty=1.1,
        )
        assert result == {
            "mirostat": 2, "mirostat_eta": 0.2, "mirostat_tau": 3.0,
        }

    def test_chaining_via_options_in(self) -> None:
        node = LLMOptionsOllamaExtra()
        upstream = {"temperature": 0.7, "top_k": 40}
        (result,) = node.build_options(
            options_in=upstream,
            enable_repeat_penalty=True, repeat_penalty=1.5,
        )
        assert result["temperature"] == 0.7
        assert result["top_k"] == 40
        assert result["repeat_penalty"] == 1.5

    def test_chaining_does_not_mutate_upstream(self) -> None:
        node = LLMOptionsOllamaExtra()
        upstream = {"temperature": 0.7}
        node.build_options(
            options_in=upstream,
            enable_repeat_penalty=True, repeat_penalty=1.5,
        )
        assert "repeat_penalty" not in upstream

    def test_all_10_params_toggle_on(self) -> None:
        """All 10 Extra params included when toggled on."""
        node = LLMOptionsOllamaExtra()
        kwargs: dict = {}
        for name, _, opts in node.PARAMS:
            kwargs[f"enable_{name}"] = True
            kwargs[name] = opts["default"]
        (result,) = node.build_options(**kwargs)
        assert len(result) == 10
        for name, _, _ in node.PARAMS:
            assert name in result


# ===========================================================================
# LM Studio Options (toggle pattern)
# ===========================================================================

class TestLMStudioToggle:
    """Toggle pattern for LM Studio's 9 parameters."""

    def test_all_toggles_off_produces_empty(self) -> None:
        node = LLMOptionsLMStudio()
        kwargs = {f"enable_{n}": False for n, _, _ in node.PARAMS}
        kwargs.update({n: opts["default"] for n, _, opts in node.PARAMS})
        (result,) = node.build_options(**kwargs)
        assert result == {}

    def test_toggle_on_includes_param(self) -> None:
        node = LLMOptionsLMStudio()
        (result,) = node.build_options(
            enable_temperature=True, temperature=0.9,
            enable_max_tokens=False, max_tokens=2048,
        )
        assert result == {"temperature": 0.9}

    def test_toggle_off_excludes_even_nondefault(self) -> None:
        node = LLMOptionsLMStudio()
        (result,) = node.build_options(
            enable_seed=False, seed=42,
        )
        assert "seed" not in result

    def test_all_9_params_toggle_on(self) -> None:
        node = LLMOptionsLMStudio()
        kwargs: dict = {}
        for name, _, opts in node.PARAMS:
            kwargs[f"enable_{name}"] = True
            kwargs[name] = opts["default"]
        (result,) = node.build_options(**kwargs)
        assert len(result) == 9
        for name, _, _ in node.PARAMS:
            assert name in result

    def test_chaining_via_options_in(self) -> None:
        node = LLMOptionsLMStudio()
        upstream = {"mirostat": 1}
        (result,) = node.build_options(
            options_in=upstream,
            enable_temperature=True, temperature=0.5,
        )
        assert result == {"mirostat": 1, "temperature": 0.5}

    def test_chaining_does_not_mutate_upstream(self) -> None:
        node = LLMOptionsLMStudio()
        upstream = {"mirostat": 1}
        node.build_options(
            options_in=upstream,
            enable_temperature=True, temperature=0.5,
        )
        assert "temperature" not in upstream

    def test_string_param_stop(self) -> None:
        node = LLMOptionsLMStudio()
        (result,) = node.build_options(enable_stop=True, stop="<|end|>")
        assert result["stop"] == "<|end|>"

    def test_multiple_params(self) -> None:
        node = LLMOptionsLMStudio()
        (result,) = node.build_options(
            enable_temperature=True, temperature=0.8,
            enable_top_p=True, top_p=0.95,
            enable_max_tokens=True, max_tokens=4096,
            enable_seed=False, seed=-1,
        )
        assert result == {"temperature": 0.8, "top_p": 0.95, "max_tokens": 4096}


# ===========================================================================
# Text-gen-webui Options (toggle pattern)
# ===========================================================================

class TestTextGenWebUIToggle:
    """Toggle pattern for text-gen-webui's 12 parameters."""

    def test_all_toggles_off_produces_empty(self) -> None:
        node = LLMOptionsTextGenWebUI()
        kwargs = {f"enable_{n}": False for n, _, _ in node.PARAMS}
        kwargs.update({n: opts["default"] for n, _, opts in node.PARAMS})
        (result,) = node.build_options(**kwargs)
        assert result == {}

    def test_toggle_on_includes_param(self) -> None:
        node = LLMOptionsTextGenWebUI()
        (result,) = node.build_options(
            enable_temperature=True, temperature=0.9,
            enable_tfs=False, tfs=1.0,
        )
        assert result == {"temperature": 0.9}

    def test_toggle_off_excludes_even_nondefault(self) -> None:
        node = LLMOptionsTextGenWebUI()
        (result,) = node.build_options(
            enable_max_tokens=False, max_tokens=4096,
        )
        assert "max_tokens" not in result

    def test_all_12_params_toggle_on(self) -> None:
        node = LLMOptionsTextGenWebUI()
        kwargs: dict = {}
        for name, _, opts in node.PARAMS:
            kwargs[f"enable_{name}"] = True
            kwargs[name] = opts["default"]
        (result,) = node.build_options(**kwargs)
        assert len(result) == 12
        for name, _, _ in node.PARAMS:
            assert name in result

    def test_chaining_via_options_in(self) -> None:
        node = LLMOptionsTextGenWebUI()
        upstream = {"num_predict": 1024}
        (result,) = node.build_options(
            options_in=upstream,
            enable_temperature=True, temperature=0.6,
        )
        assert result == {"num_predict": 1024, "temperature": 0.6}

    def test_chaining_does_not_mutate_upstream(self) -> None:
        node = LLMOptionsTextGenWebUI()
        upstream = {"num_predict": 1024}
        node.build_options(
            options_in=upstream,
            enable_temperature=True, temperature=0.6,
        )
        assert "temperature" not in upstream

    def test_tfs_param(self) -> None:
        """text-gen-webui uses 'tfs' not 'tfs_z'."""
        node = LLMOptionsTextGenWebUI()
        (result,) = node.build_options(enable_tfs=True, tfs=0.95)
        assert result["tfs"] == 0.95

    def test_typical_p_and_min_p(self) -> None:
        node = LLMOptionsTextGenWebUI()
        (result,) = node.build_options(
            enable_typical_p=True, typical_p=0.8,
            enable_min_p=True, min_p=0.1,
        )
        assert result == {"typical_p": 0.8, "min_p": 0.1}

    def test_multiple_params(self) -> None:
        node = LLMOptionsTextGenWebUI()
        (result,) = node.build_options(
            enable_temperature=True, temperature=0.7,
            enable_top_p=True, top_p=0.9,
            enable_max_tokens=True, max_tokens=512,
            enable_seed=True, seed=42,
            enable_repeat_penalty=False, repeat_penalty=1.1,
        )
        assert result == {
            "temperature": 0.7, "top_p": 0.9,
            "max_tokens": 512, "seed": 42,
        }
