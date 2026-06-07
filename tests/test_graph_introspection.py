"""Tests for PROMPT reverse-indexing used in unload deferral."""

from __future__ import annotations

import unittest

from graph.introspection import find_downstream_nodes, has_downstream_gen_node


class TestFindDownstreamNodes(unittest.TestCase):
    def test_finds_direct_connection(self) -> None:
        prompt = {
            "10": {
                "class_type": "LLMGenerateAdvanced",
                "inputs": {"meta": ["9", 1], "prompt": ["x", 0]},
            },
            "9": {"class_type": "LLMGenerate", "inputs": {}},
        }
        out = find_downstream_nodes(prompt, "9", 1)
        self.assertEqual(out, [("10", "LLMGenerateAdvanced", "meta")])


class TestHasDownstreamGenNode(unittest.TestCase):
    def test_true_when_meta_connects_to_advanced(self) -> None:
        prompt = {
            "2": {
                "class_type": "LLMGenerateAdvanced",
                "inputs": {"meta": ["1", 1]},
            },
        }
        self.assertTrue(has_downstream_gen_node(prompt, "1", 1))

    def test_true_when_meta_connects_to_basic(self) -> None:
        prompt = {
            "2": {
                "class_type": "LLMGenerate",
                "inputs": {"provider": ["0", 0], "meta": ["1", 1]},
            },
        }
        self.assertTrue(has_downstream_gen_node(prompt, "1", 1))

    def test_false_when_no_downstream(self) -> None:
        prompt = {"1": {"class_type": "LLMGenerate", "inputs": {}}}
        self.assertFalse(has_downstream_gen_node(prompt, "1", 1))


if __name__ == "__main__":
    unittest.main()
