"""Resolve API credentials at HTTP time — never stored in provider dicts."""

from __future__ import annotations

try:
    from . import get_api_key, get_textgen_auth_keys
except ImportError:
    from config import get_api_key, get_textgen_auth_keys

_SECRET_KEYS = frozenset({"api_key", "admin_key"})

# OAI-shaped backends share a documented fallback to providers.oai_compat so
# one pasted key works for LM Studio / llama.cpp / OpenAI / generic proxies
# the same way Textgen already merges via get_textgen_auth_keys().
_OAI_COMPAT_FALLBACK_BACKENDS = frozenset(
    {"generic", "openai", "lm_studio", "llamacpp", "oai_compat"},
)


def consulted_auth_slots(backend: str) -> list[str]:
    """Config slot names consulted for *backend* (names only — no secrets).

    Textgen uses ``text_gen_webui`` then ``oai_compat`` (via
    ``get_textgen_auth_keys``). Other OAI-shaped backends use their own slot
    then ``oai_compat``. Unknown backends consult only themselves.
    """
    if backend == "text_gen_webui":
        return ["text_gen_webui", "oai_compat"]
    slots: list[str] = []
    if backend:
        slots.append(backend)
    if backend in _OAI_COMPAT_FALLBACK_BACKENDS and "oai_compat" not in slots:
        slots.append("oai_compat")
    return slots


def api_keys_for_backend(backend: str) -> list[str]:
    """Unique API keys from the same chain as ``resolve_provider_auth``.

    Used by model-list / ensure-loaded retries so list and generate agree on
    which config slots can supply a Bearer token. Never returns admin-only
    secrets for non-Textgen backends.
    """
    if backend == "text_gen_webui":
        api_key, admin_key = get_textgen_auth_keys()
        out: list[str] = []
        seen: set[str] = set()
        for k in (api_key, admin_key):
            if k and k not in seen:
                seen.add(k)
                out.append(k)
        return out

    out = []
    seen = set()
    for slot in consulted_auth_slots(backend):
        key = get_api_key(slot)
        if key and key not in seen:
            seen.add(key)
            out.append(key)
    return out


def resolve_provider_auth(provider: dict) -> tuple[str | None, str | None]:
    """Return ``(api_key, admin_key)`` for the given provider context.

    Textgen keeps the dual-role merge in ``get_textgen_auth_keys``. All other
    OAI-shaped backends resolve ``providers.<backend>.api_key`` then fall back
    to ``providers.oai_compat.api_key`` (and matching env vars via
    ``get_api_key``).
    """
    backend = provider.get("backend", "") or ""

    if backend == "text_gen_webui":
        return get_textgen_auth_keys()

    for slot in consulted_auth_slots(backend):
        api_key = get_api_key(slot)
        if api_key:
            return api_key, None
    return None, None


def public_provider(provider: dict) -> dict:
    """Return a provider dict safe for ComfyUI outputs (strips secrets)."""
    return {k: v for k, v in provider.items() if k not in _SECRET_KEYS}


def describe_auth_status(backend: str) -> str:
    """Human status line for UI — names/presence only, never key material."""
    backend = backend or "generic"

    if backend == "text_gen_webui":
        api_key, admin_key = get_textgen_auth_keys()
        if api_key and admin_key:
            return "auth: Textgen API ok, admin ok"
        if api_key and not admin_key:
            return "auth: Textgen API ok, admin missing"
        if admin_key and not api_key:
            return "auth: Textgen API missing, admin ok"
        return (
            "auth: missing (set providers.text_gen_webui.api_key "
            "or providers.oai_compat.api_key)"
        )

    slots = consulted_auth_slots(backend)
    for slot in slots:
        if get_api_key(slot):
            if slot == backend:
                return f"auth: ok ({slot})"
            return f"auth: ok via {slot} fallback"

    if backend in {"lm_studio", "llamacpp", "generic", "ollama"}:
        return "auth: n/a (local, no key required)"
    if backend == "openai":
        return (
            "auth: missing (set providers.openai.api_key "
            "or providers.oai_compat.api_key)"
        )
    return "auth: missing (set providers.oai_compat.api_key or …)"

