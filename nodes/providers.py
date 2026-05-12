"""Provider nodes — generic OAI-compatible."""

from ..config import get_api_key, get_config, get_textgen_auth_keys
from ..detection import detect_backend, normalize_oai_base_url


class LLMProviderOAICompat:
    """Generic OpenAI-compatible provider node.

    Auto-detects the backend at the given URL via API fingerprinting.
    Supports LM Studio, Textgen, OpenAI, llama.cpp, and any OAI-compat endpoint.
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
        fallback = model_fallback.strip() if model_fallback else ""
        resolved_model = fallback if fallback else model

        url = normalize_oai_base_url(url)

        cfg = get_config()
        providers_cfg = cfg.get("providers", {})

        # Detect backend type
        preliminary_key = get_api_key("oai_compat")
        backend = detect_backend(url, api_key=preliminary_key)

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
