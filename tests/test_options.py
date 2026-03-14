"""Tests for Ollama Core Options node (sentinel pattern)."""

from __future__ import annotations

from nodes.options_ollama import LLMOptionsOllamaCore


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
        (result,) = node.build_options(top_k=40, seed=42, num_predict=1024, num_ctx=4096)
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
