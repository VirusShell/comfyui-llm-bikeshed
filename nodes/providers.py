"""Provider nodes — generic OAI-compatible and dedicated Textgen."""

import logging

try:
    from ..config import get_api_key, get_config, get_textgen_auth_keys
    from ..detection import detect_backend, normalize_oai_base_url
except ImportError:
    from config import get_api_key, get_config, get_textgen_auth_keys
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
    def VALIDATE_INPUTS(cls, model: str = "", **kwargs: object) -> bool:  # noqa: N802
        """Accept any model string — list is dynamically populated by JS."""
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
        preliminary_key = get_api_key("oai_compat")
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

        # Credentials (Textgen: single password, often stored under oai_compat)
        if backend == "text_gen_webui":
            api_key, admin_key = get_textgen_auth_keys()
        else:
            api_key = get_api_key(backend)
            if not api_key and backend in ("generic", "openai"):
                api_key = get_api_key("oai_compat")
            admin_key = None

        provider = {
            "backend": backend,
            "adapter": "oai_compat",
            "url": url.rstrip("/"),
            "model": resolved_model,
            "timeout": timeout,
            "api_key": api_key,
            "admin_key": admin_key,
            "lifecycle": lifecycle,
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
    def VALIDATE_INPUTS(cls, model: str = "", **kwargs: object) -> bool:  # noqa: N802
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
        api_key, admin_key = get_textgen_auth_keys()

        lifecycle: dict | None = (
            {"type": "text_gen_webui"} if manage_model_memory else None
        )

        provider = {
            "backend": "text_gen_webui",
            "adapter": "oai_compat",
            "url": url.rstrip("/"),
            "model": resolved_model,
            "timeout": timeout,
            "api_key": api_key,
            "admin_key": admin_key,
            "lifecycle": lifecycle,
        }
        return (provider,)
