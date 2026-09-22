"""Provider nodes — OAI-compatible, Textgen, and adaptive Connection."""

import logging

try:
    from ..config import get_config
    from ..config.auth import resolve_provider_auth
    from ..detection import detect_backend, normalize_oai_base_url
except ImportError:
    from config import get_config
    from config.auth import resolve_provider_auth
    from detection import detect_backend, normalize_oai_base_url

logger = logging.getLogger("llm-bikeshed")

_OAI_COMPAT_TEXTGEN_HINT_LOGGED = False


class LLMProviderOAICompat:
    """Generic OpenAI-compatible provider node.

    Auto-detects the backend at the given URL via API fingerprinting.
    Supports LM Studio, Textgen, OpenAI, llama.cpp, and any OAI-compat endpoint.

    For **oobabooga Textgen**, prefer **LLM Provider: Textgen**
    (``LLMProviderTextGenWebUI``): fixed backend, ``http://localhost:5000``
    default, Textgen-only model refresh (no fingerprinting), and integrated
    ``manage_model_memory`` — this node remains valid for mixed or migrated
    workflows.
    """

    RETURN_TYPES = ("LLM_PROVIDER",)
    RETURN_NAMES = ("provider",)
    FUNCTION = "build_provider"
    CATEGORY = "LLM Bikeshed/providers"

    @classmethod
    def INPUT_TYPES(cls) -> dict:  # noqa: N802
        return {
            "required": {
                "url": ("STRING", {"default": "http://localhost:1234"}),
                "model": (["(refresh to load)"],),
            },
            "optional": {
                "model_fallback": (
                    "STRING",
                    {"default": "", "forceInput": True},
                ),
                "lifecycle": ("LLM_LIFECYCLE",),
            },
        }

    @classmethod
    def VALIDATE_INPUTS(  # noqa: N802
        cls,
        model: str = "",
        model_fallback: str = "",
        **kwargs: object,
    ) -> bool | str:
        """Reject placeholder model ids before queueing the workflow."""
        resolved = (model_fallback or "").strip() or (model or "").strip()
        if not resolved or resolved.startswith("("):
            return (
                "Select a model from the dropdown "
                "(click Refresh Models if the list is empty)"
            )
        return True

    def build_provider(
        self,
        url: str,
        model: str,
        model_fallback: str = "",
        lifecycle: dict | None = None,
    ) -> tuple[dict]:
        """Build LLM_PROVIDER dict with auto-detected backend type."""
        global _OAI_COMPAT_TEXTGEN_HINT_LOGGED

        fallback = model_fallback.strip() if model_fallback else ""
        resolved_model = fallback if fallback else model

        url = normalize_oai_base_url(url)

        cfg = get_config()
        providers_cfg = cfg.get("providers", {})

        # Detect backend type
        preliminary_key, _ = resolve_provider_auth({"backend": "oai_compat"})
        backend = detect_backend(url, api_key=preliminary_key)

        if backend == "text_gen_webui" and not _OAI_COMPAT_TEXTGEN_HINT_LOGGED:
            _OAI_COMPAT_TEXTGEN_HINT_LOGGED = True
            logger.info(
                "Backend at %s is Textgen — prefer node \"LLM Provider: Textgen\" "
                "(LLMProviderTextGenWebUI) for defaults and integrated VRAM controls. "
                "OAI Compatible continues to work for existing graphs.",
                url,
            )

        # Resolve timeout: try detected backend, then oai_compat, then default
        timeout = (
            providers_cfg.get(backend, {}).get("timeout")
            or providers_cfg.get("oai_compat", {}).get("timeout")
            or 120
        )

        provider = {
            "backend": backend,
            "adapter": "oai_compat",
            "url": url.rstrip("/"),
            "model": resolved_model,
            "timeout": timeout,
            "lifecycle": lifecycle,
            "load_before_generate": backend == "text_gen_webui",
        }
        return (provider,)


class LLMProviderTextGenWebUI:
    """Dedicated provider for oobabooga Textgen (OpenAI-compatible chat API)."""

    RETURN_TYPES = ("LLM_PROVIDER",)
    RETURN_NAMES = ("provider",)
    FUNCTION = "build_provider"
    CATEGORY = "LLM Bikeshed/providers"

    @classmethod
    def INPUT_TYPES(cls) -> dict:  # noqa: N802
        return {
            "required": {
                "url": ("STRING", {"default": "http://localhost:5000"}),
                "model": (["(refresh to load)"],),
                "manage_model_memory": (
                    "BOOLEAN",
                    {
                        "default": True,
                        "label_on": "ON",
                        "label_off": "OFF",
                    },
                ),
            },
            "optional": {
                "model_fallback": (
                    "STRING",
                    {"default": "", "forceInput": True},
                ),
            },
        }

    @classmethod
    def VALIDATE_INPUTS(  # noqa: N802
        cls,
        model: str = "",
        model_fallback: str = "",
        **kwargs: object,
    ) -> bool | str:
        resolved = (model_fallback or "").strip() or (model or "").strip()
        if not resolved or resolved.startswith("("):
            return (
                "Select a model from the dropdown "
                "(click Refresh Models if the list is empty)"
            )
        return True

    def build_provider(
        self,
        url: str,
        model: str,
        manage_model_memory: bool = True,
        model_fallback: str = "",
    ) -> tuple[dict]:
        """Build LLM_PROVIDER for Textgen with optional integrated lifecycle."""
        fallback = model_fallback.strip() if model_fallback else ""
        resolved_model = fallback if fallback else model

        url = normalize_oai_base_url(url)

        cfg = get_config()
        providers_cfg = cfg.get("providers", {})
        timeout = (
            providers_cfg.get("text_gen_webui", {}).get("timeout")
            or providers_cfg.get("oai_compat", {}).get("timeout")
            or 120
        )
        lifecycle: dict | None = (
            {"type": "text_gen_webui"} if manage_model_memory else None
        )

        provider = {
            "backend": "text_gen_webui",
            "adapter": "oai_compat",
            "url": url.rstrip("/"),
            "model": resolved_model,
            "timeout": timeout,
            "lifecycle": lifecycle,
            "load_before_generate": manage_model_memory,
        }
        return (provider,)


# ---------------------------------------------------------------------------
# LLM Connection — adaptive host face (v4 surface)
# ---------------------------------------------------------------------------

HOST_MODE_AUTO = "Auto (detect)"
HOST_MODE_CHOICES = (
    HOST_MODE_AUTO,
    "LM Studio",
    "Textgen",
    "llama.cpp",
    "OpenAI / OAI-compat",
    "Generic OAI",
)

_HOST_MODE_TO_BACKEND = {
    "LM Studio": "lm_studio",
    "Textgen": "text_gen_webui",
    "llama.cpp": "llamacpp",
    "OpenAI / OAI-compat": "openai",
    "Generic OAI": "generic",
}

# Modes where pack can feed a model COMBO (catalog). llama.cpp / generic = STRING.
CATALOG_BACKENDS = frozenset({"text_gen_webui", "lm_studio", "openai"})
# Modes with on-node VRAM / lifecycle face knobs.
FACE_TEXTGEN = "text_gen_webui"
FACE_LM_STUDIO = "lm_studio"
LOAD_CAPABLE_BACKENDS = frozenset({"text_gen_webui", "lm_studio"})


def resolve_connection_backends(
    url: str,
    host_mode: str,
    *,
    api_key: str | None = None,
) -> tuple[str, str, str]:
    """Return ``(detected, effective, face)`` backend slugs.

    *effective* is what goes into ``LLM_PROVIDER["backend"]`` and drives
    catalog / lifecycle. *face* matches *effective* except Auto+ollama uses
    a Generic OAI face (native Ollama out of scope). Override always wins.
    """
    preliminary = api_key
    if preliminary is None:
        preliminary, _ = resolve_provider_auth({"backend": "oai_compat"})
    detected = detect_backend(normalize_oai_base_url(url), api_key=preliminary)

    mode = (host_mode or HOST_MODE_AUTO).strip()
    if mode != HOST_MODE_AUTO and mode in _HOST_MODE_TO_BACKEND:
        effective = _HOST_MODE_TO_BACKEND[mode]
        return detected, effective, effective

    # Auto (detect)
    if detected == "ollama":
        return detected, "generic", "generic"
    return detected, detected, detected


def _connection_timeout(providers_cfg: dict, backend: str, timeout: int) -> int:
    if timeout and int(timeout) > 0:
        return int(timeout)
    return (
        providers_cfg.get(backend, {}).get("timeout")
        or providers_cfg.get("oai_compat", {}).get("timeout")
        or 120
    )


def _connection_lifecycle(
    face: str,
    manage_model_memory: bool,
    ttl: int,
    context_length: int,
) -> tuple[dict | None, bool]:
    """Embed lifecycle for face mode; ignore off-mode knobs.

    Returns ``(lifecycle, load_before_generate)``.
    """
    if face == FACE_TEXTGEN:
        if manage_model_memory:
            return {"type": "text_gen_webui"}, True
        return None, False
    if face == FACE_LM_STUDIO:
        return (
            {
                "type": "lm_studio",
                "ttl": int(ttl) if ttl is not None else 30,
                "context_length": (
                    int(context_length) if context_length and int(context_length) > 0
                    else None
                ),
            },
            False,
        )
    return None, False


class LLMConnection:
    """Adaptive connection node — host mode + embedded VRAM face (no auth widgets).

    Old ``LLMProvider*`` / lifecycle nodes stay registered beside this class.
    """

    RETURN_TYPES = ("LLM_PROVIDER",)
    RETURN_NAMES = ("provider",)
    FUNCTION = "build_provider"
    CATEGORY = "LLM Bikeshed/providers"
    DESCRIPTION = (
        "Adaptive LLM connection: pick host mode (or Auto), set URL/model, use "
        "on-node VRAM knobs for Textgen/LM Studio. API keys stay in config.yaml / "
        "env. Prefer this over separate Provider + Lifecycle nodes for new graphs."
    )

    @classmethod
    def INPUT_TYPES(cls) -> dict:  # noqa: N802
        return {
            "required": {
                "url": ("STRING", {"default": "http://localhost:1234"}),
                "host_mode": (list(HOST_MODE_CHOICES),),
                "model": (["(refresh to load)"],),
            },
            "optional": {
                "model_fallback": (
                    "STRING",
                    {"default": "", "forceInput": True},
                ),
                "timeout": (
                    "INT",
                    {
                        "default": 0,
                        "min": 0,
                        "max": 86400,
                        "advanced": True,
                        "tooltip": (
                            "HTTP timeout seconds. 0 = use config for the "
                            "effective backend, then oai_compat, then 120."
                        ),
                    },
                ),
                "manage_model_memory": (
                    "BOOLEAN",
                    {
                        "default": True,
                        "label_on": "ON",
                        "label_off": "OFF",
                        "tooltip": (
                            "Textgen face: load before generate and unload after "
                            "chain when ON. Ignored in other host modes."
                        ),
                    },
                ),
                "ttl": (
                    "INT",
                    {
                        "default": 30,
                        "min": 0,
                        "tooltip": (
                            "LM Studio face: seconds to keep model loaded after "
                            "each request. Ignored in other host modes."
                        ),
                    },
                ),
                "context_length": (
                    "INT",
                    {
                        "default": 0,
                        "min": 0,
                        "max": 1048576,
                        "tooltip": (
                            "LM Studio face: context window on explicit load. "
                            "0 = model default. Ignored in other host modes."
                        ),
                    },
                ),
                "ensure_load_on_select": (
                    "BOOLEAN",
                    {
                        "default": False,
                        "label_on": "ON",
                        "label_off": "OFF",
                        "tooltip": (
                            "Textgen/LM Studio: when ON, changing the model "
                            "dropdown may load weights. URL changes never load. "
                            "Default OFF."
                        ),
                    },
                ),
            },
        }

    @classmethod
    def VALIDATE_INPUTS(  # noqa: N802
        cls,
        model: str = "",
        model_fallback: str = "",
        **kwargs: object,
    ) -> bool | str:
        resolved = (model_fallback or "").strip() or (model or "").strip()
        if not resolved or resolved.startswith("("):
            return (
                "Set a model id (dropdown or type-in for llama.cpp / generic; "
                "click Refresh Models if the catalog is empty)"
            )
        return True

    def build_provider(
        self,
        url: str,
        host_mode: str,
        model: str,
        model_fallback: str = "",
        timeout: int = 0,
        manage_model_memory: bool = True,
        ttl: int = 30,
        context_length: int = 0,
        ensure_load_on_select: bool = False,  # noqa: ARG002 — UI-only
    ) -> tuple[dict]:
        """Build secret-free LLM_PROVIDER from connection face widgets."""
        fallback = model_fallback.strip() if model_fallback else ""
        resolved_model = fallback if fallback else model

        url = normalize_oai_base_url(url)
        _detected, effective, face = resolve_connection_backends(url, host_mode)

        cfg = get_config()
        providers_cfg = cfg.get("providers", {})
        resolved_timeout = _connection_timeout(providers_cfg, effective, timeout)
        lifecycle, load_before = _connection_lifecycle(
            face, manage_model_memory, ttl, context_length,
        )

        provider = {
            "backend": effective,
            "adapter": "oai_compat",
            "url": url.rstrip("/"),
            "model": resolved_model,
            "timeout": resolved_timeout,
            "lifecycle": lifecycle,
            "load_before_generate": load_before,
        }
        return (provider,)

