"""Resolve API credentials at HTTP time — never stored in provider dicts."""

from __future__ import annotations

try:
    from . import get_api_key, get_textgen_auth_keys
except ImportError:
    from config import get_api_key, get_textgen_auth_keys

_SECRET_KEYS = frozenset({"api_key", "admin_key"})


def resolve_provider_auth(provider: dict) -> tuple[str | None, str | None]:
    """Return ``(api_key, admin_key)`` for the given provider context."""
    backend = provider.get("backend", "")

    if backend == "text_gen_webui":
        return get_textgen_auth_keys()

    api_key = get_api_key(backend)
    if not api_key and backend in ("generic", "openai"):
        api_key = get_api_key("oai_compat")
    return api_key, None


def public_provider(provider: dict) -> dict:
    """Return a provider dict safe for ComfyUI outputs (strips secrets)."""
    return {k: v for k, v in provider.items() if k not in _SECRET_KEYS}
