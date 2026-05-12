"""Adapter registry — singleton lookup by adapter type key."""

from __future__ import annotations

from .base import LLMAdapter
from .oai_compat import OAICompatAdapter

_ADAPTERS: dict[str, LLMAdapter] = {
    "oai_compat": OAICompatAdapter(),
}


def get_adapter(adapter_type: str) -> LLMAdapter:
    """Return the singleton adapter for *adapter_type*.

    Raises ``KeyError`` if the adapter type is not registered.
    """
    return _ADAPTERS[adapter_type]
