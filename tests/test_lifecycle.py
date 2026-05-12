"""Tests for lifecycle nodes."""

from __future__ import annotations

from nodes.lifecycle import LLMLifecycleLMStudio, LLMLifecycleTextGenWebUI


class TestLMStudioLifecycle:
    """LLMLifecycleLMStudio builds correct dict."""

    def test_builds_dict_with_ttl_and_context_length(self) -> None:
        node = LLMLifecycleLMStudio()
        (result,) = node.build_lifecycle(ttl=60, context_length=4096)
        assert result == {
            "type": "lm_studio",
            "ttl": 60,
            "context_length": 4096,
        }

    def test_context_length_zero_becomes_none(self) -> None:
        node = LLMLifecycleLMStudio()
        (result,) = node.build_lifecycle(ttl=30, context_length=0)
        assert result["context_length"] is None

    def test_default_values(self) -> None:
        node = LLMLifecycleLMStudio()
        (result,) = node.build_lifecycle(ttl=30, context_length=0)
        assert result["type"] == "lm_studio"
        assert result["ttl"] == 30


class TestTextGenWebUILifecycle:
    """LLMLifecycleTextGenWebUI builds presence-only dict."""

    def test_builds_presence_dict(self) -> None:
        node = LLMLifecycleTextGenWebUI()
        (result,) = node.build_lifecycle(manage_model_memory=True)
        assert result == {"type": "text_gen_webui"}

    def test_output_type(self) -> None:
        assert LLMLifecycleTextGenWebUI.RETURN_TYPES == ("LLM_LIFECYCLE",)
