"""Graph introspection utilities for unload deferral.

Provides functions to reverse-index the ComfyUI PROMPT dict and determine
whether a node's output connects to a downstream generation node.
"""

from __future__ import annotations

from typing import Any

GENERATION_CLASS_TYPES = {
    "LLMGenerate",
    "LLMGenerateAdvanced",
}


def find_downstream_nodes(
    prompt: dict[str, Any],
    node_id: str,
    output_index: int,
) -> list[tuple[str, str, str]]:
    """Find all nodes whose inputs connect to [node_id, output_index].

    Args:
        prompt: The ComfyUI PROMPT dict (node_id -> node_info).
        node_id: The source node ID to search from.
        output_index: The output slot index on the source node.

    Returns:
        List of (node_id, class_type, input_name) tuples for downstream nodes.
    """
    downstream: list[tuple[str, str, str]] = []
    for nid, node_info in prompt.items():
        inputs = node_info.get("inputs", {})
        for input_name, value in inputs.items():
            if (
                isinstance(value, list)
                and len(value) == 2
                and str(value[0]) == str(node_id)
                and value[1] == output_index
            ):
                downstream.append((nid, node_info.get("class_type", ""), input_name))
    return downstream


def has_downstream_gen_node(
    prompt: dict[str, Any],
    node_id: str,
    meta_output_index: int,
) -> bool:
    """Check if any downstream node is a generation node.

    Args:
        prompt: The ComfyUI PROMPT dict.
        node_id: The source node ID.
        meta_output_index: The output slot index to check.

    Returns:
        True if any downstream node's class_type is in GENERATION_CLASS_TYPES.
    """
    downstream = find_downstream_nodes(prompt, node_id, meta_output_index)
    return any(ct in GENERATION_CLASS_TYPES for _, ct, _ in downstream)
