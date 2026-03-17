"""Adapter registry — singleton lookup by adapter type key."""

from __future__ import annotations

from .base import LLMAdapter
from .oai_compat import OAICompatAdapter
from .ollama import OllamaAdapter

_ADAPTERS: dict[str, LLMAdapter] = {
    "oai_compat": OAICompatAdapter(),
    "ollama_native": OllamaAdapter(),
}


def get_adapter(adapter_type: str) -> LLMAdapter:
    """Return the singleton adapter for *adapter_type*.

    Raises ``KeyError`` if the adapter type is not registered.
    """
    return _ADAPTERS[adapter_type]
