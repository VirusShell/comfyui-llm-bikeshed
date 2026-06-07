"""Tests for Options nodes (LM Studio, Textgen toggle patterns)."""

from __future__ import annotations

from nodes.options_base import PARAM_NAME_MAP
from nodes.options_lm_studio import LLMOptionsLMStudio
from nodes.options_text_gen_webui import LLMOptionsTextGenWebUI

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
            assert PARAM_NAME_MAP.get(name, name) in result

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
        (result,) = node.build_options(
            enable_stop_string=True, stop_string="<|end|>",
        )
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
            assert PARAM_NAME_MAP.get(name, name) in result

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
