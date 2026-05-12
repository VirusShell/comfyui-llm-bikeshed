"""Regression: Ollama-first-class surface removed from the pack."""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest


def test_adapter_registry_excludes_ollama_native() -> None:
    from adapters import get_adapter

    with pytest.raises(KeyError):
        get_adapter("ollama_native")


def test_provider_module_has_no_ollama_node() -> None:
    root = Path(__file__).resolve().parents[1]
    text = (root / "nodes" / "providers.py").read_text(encoding="utf-8")
    assert "LLMProviderOllama" not in text


def test_options_ollama_module_absent() -> None:
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("nodes.options_ollama")
