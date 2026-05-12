"""Tests for graph introspection utilities."""

from __future__ import annotations

from graph.introspection import (
    GENERATION_CLASS_TYPES,
    find_downstream_nodes,
    has_downstream_gen_node,
)

# ---------------------------------------------------------------------------
# Sample PROMPT dicts
# ---------------------------------------------------------------------------

# Simple chain: provider -> generate
PROMPT_SIMPLE: dict = {
    "1": {
        "class_type": "LLMProviderOAICompat",
        "inputs": {"host": "http://localhost:11434", "model": "llama3"},
    },
    "2": {
        "class_type": "LLMGenerate",
        "inputs": {
            "system_prompt": "You are helpful.",
            "user_prompt": "Hello",
            "provider": ["1", 0],
        },
    },
}

# Provider feeding two generation nodes
PROMPT_MULTI_DOWNSTREAM: dict = {
    "10": {
        "class_type": "LLMProviderOAICompat",
        "inputs": {"host": "http://localhost:11434"},
    },
    "11": {
        "class_type": "LLMGenerate",
        "inputs": {"provider": ["10", 0], "user_prompt": "A"},
    },
    "12": {
        "class_type": "LLMGenerateAdvanced",
        "inputs": {"provider": ["10", 0], "user_prompt": "B"},
    },
}

# Provider with no downstream connections
PROMPT_NO_DOWNSTREAM: dict = {
    "20": {
        "class_type": "LLMProviderOAICompat",
        "inputs": {"host": "http://localhost:11434"},
    },
}

# Provider connected to a non-generation node only
PROMPT_NON_GEN_DOWNSTREAM: dict = {
    "30": {
        "class_type": "LLMProviderOAICompat",
        "inputs": {"host": "http://localhost:11434"},
    },
    "31": {
        "class_type": "SomeOtherNode",
        "inputs": {"data": ["30", 0]},
    },
}

# Mixed: gen and non-gen downstream
PROMPT_MIXED: dict = {
    "40": {
        "class_type": "LLMProviderOAICompat",
        "inputs": {},
    },
    "41": {
        "class_type": "LLMGenerate",
        "inputs": {"provider": ["40", 0]},
    },
    "42": {
        "class_type": "DebugNode",
        "inputs": {"input": ["40", 0]},
    },
}


# ---------------------------------------------------------------------------
# find_downstream_nodes
# ---------------------------------------------------------------------------


class TestFindDownstreamNodes:
    """Test find_downstream_nodes with various PROMPT structures."""

    def test_single_downstream(self) -> None:
        result = find_downstream_nodes(PROMPT_SIMPLE, "1", 0)
        assert len(result) == 1
        nid, class_type, input_name = result[0]
        assert nid == "2"
        assert class_type == "LLMGenerate"
        assert input_name == "provider"

    def test_multiple_downstream(self) -> None:
        result = find_downstream_nodes(PROMPT_MULTI_DOWNSTREAM, "10", 0)
        assert len(result) == 2
        class_types = {ct for _, ct, _ in result}
        assert class_types == {"LLMGenerate", "LLMGenerateAdvanced"}

    def test_no_downstream(self) -> None:
        result = find_downstream_nodes(PROMPT_NO_DOWNSTREAM, "20", 0)
        assert result == []

    def test_wrong_output_index(self) -> None:
        result = find_downstream_nodes(PROMPT_SIMPLE, "1", 1)
        assert result == []

    def test_nonexistent_node_id(self) -> None:
        result = find_downstream_nodes(PROMPT_SIMPLE, "999", 0)
        assert result == []

    def test_non_gen_downstream(self) -> None:
        result = find_downstream_nodes(PROMPT_NON_GEN_DOWNSTREAM, "30", 0)
        assert len(result) == 1
        assert result[0][1] == "SomeOtherNode"

    def test_mixed_downstream(self) -> None:
        result = find_downstream_nodes(PROMPT_MIXED, "40", 0)
        assert len(result) == 2
        class_types = {ct for _, ct, _ in result}
        assert class_types == {"LLMGenerate", "DebugNode"}

    def test_empty_prompt(self) -> None:
        result = find_downstream_nodes({}, "1", 0)
        assert result == []

    def test_node_id_coerced_to_string(self) -> None:
        """Integer node_id in link should still match string node_id arg."""
        prompt = {
            "1": {"class_type": "Source", "inputs": {}},
            "2": {"class_type": "Sink", "inputs": {"data": [1, 0]}},
        }
        result = find_downstream_nodes(prompt, "1", 0)
        assert len(result) == 1


# ---------------------------------------------------------------------------
# has_downstream_gen_node
# ---------------------------------------------------------------------------


class TestHasDownstreamGenNode:
    """Test has_downstream_gen_node detection."""

    def test_gen_node_downstream(self) -> None:
        assert has_downstream_gen_node(PROMPT_SIMPLE, "1", 0) is True

    def test_advanced_gen_node_downstream(self) -> None:
        prompt = {
            "1": {"class_type": "Source", "inputs": {}},
            "2": {
                "class_type": "LLMGenerateAdvanced",
                "inputs": {"provider": ["1", 0]},
            },
        }
        assert has_downstream_gen_node(prompt, "1", 0) is True

    def test_no_gen_node_downstream(self) -> None:
        assert has_downstream_gen_node(PROMPT_NON_GEN_DOWNSTREAM, "30", 0) is False

    def test_no_downstream_at_all(self) -> None:
        assert has_downstream_gen_node(PROMPT_NO_DOWNSTREAM, "20", 0) is False

    def test_mixed_returns_true(self) -> None:
        """If at least one downstream is a gen node, return True."""
        assert has_downstream_gen_node(PROMPT_MIXED, "40", 0) is True

    def test_multiple_gen_nodes(self) -> None:
        assert has_downstream_gen_node(PROMPT_MULTI_DOWNSTREAM, "10", 0) is True


# ---------------------------------------------------------------------------
# GENERATION_CLASS_TYPES constant
# ---------------------------------------------------------------------------


class TestGenerationClassTypes:
    """Verify the generation class types constant."""

    def test_contains_expected_types(self) -> None:
        assert "LLMGenerate" in GENERATION_CLASS_TYPES
        assert "LLMGenerateAdvanced" in GENERATION_CLASS_TYPES

    def test_is_set(self) -> None:
        assert isinstance(GENERATION_CLASS_TYPES, set)
