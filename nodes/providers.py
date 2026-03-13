"""Provider nodes — one class per supported LLM backend."""

from config import get_api_key, get_config


class LLMProviderLMStudio:
    """LM Studio provider node. Outputs LLM_PROVIDER dict with oai_compat adapter."""

    RETURN_TYPES = ("LLM_PROVIDER",)
    RETURN_NAMES = ("provider",)
    FUNCTION = "build_provider"
    CATEGORY = "LLM Bikeshed/providers"

    @classmethod
    def INPUT_TYPES(cls) -> dict:
        return {
            "required": {
                "url": ("STRING", {"default": "http://localhost:1234"}),
                "model": (["(refresh to load)"],),
                "ttl": ("INT", {"default": 30, "min": 0}),
            },
            "optional": {
                "model_fallback": ("STRING", {"default": "", "defaultInput": True}),
            },
        }

    def build_provider(
        self,
        url: str,
        model: str,
        ttl: int,
        model_fallback: str = "",
    ) -> tuple[dict]:
        """Build LLM_PROVIDER dict for LM Studio backend."""
        fallback = model_fallback.strip() if model_fallback else ""
        resolved_model = fallback if fallback else model

        cfg = get_config()
        timeout = cfg.get("providers", {}).get("lm_studio", {}).get("timeout", 120)
        api_key = get_api_key("lm_studio")

        provider = {
            "backend": "lm_studio",
            "adapter": "oai_compat",
            "url": url.rstrip("/"),
            "model": resolved_model,
            "timeout": timeout,
            "api_key": api_key,
            "admin_key": None,
            "memory": {
                "ttl": ttl,
                "keep_alive": None,
            },
        }
        return (provider,)


class LLMProviderOllama:
    """Ollama provider node. Outputs LLM_PROVIDER dict with ollama_native adapter."""

    RETURN_TYPES = ("LLM_PROVIDER",)
    RETURN_NAMES = ("provider",)
    FUNCTION = "build_provider"
    CATEGORY = "LLM Bikeshed/providers"

    @classmethod
    def INPUT_TYPES(cls) -> dict:
        return {
            "required": {
                "url": ("STRING", {"default": "http://localhost:11434"}),
                "model": (["(refresh to load)"],),
                "keep_alive": ("STRING", {"default": "30s"}),
            },
            "optional": {
                "model_fallback": ("STRING", {"default": "", "defaultInput": True}),
            },
        }

    def build_provider(
        self,
        url: str,
        model: str,
        keep_alive: str,
        model_fallback: str = "",
    ) -> tuple[dict]:
        """Build LLM_PROVIDER dict for Ollama backend."""
        fallback = model_fallback.strip() if model_fallback else ""
        resolved_model = fallback if fallback else model

        cfg = get_config()
        timeout = cfg.get("providers", {}).get("ollama", {}).get("timeout", 120)

        provider = {
            "backend": "ollama",
            "adapter": "ollama_native",
            "url": url.rstrip("/"),
            "model": resolved_model,
            "timeout": timeout,
            "api_key": None,
            "admin_key": None,
            "memory": {
                "keep_alive": keep_alive,
                "ttl": None,
            },
        }
        return (provider,)
