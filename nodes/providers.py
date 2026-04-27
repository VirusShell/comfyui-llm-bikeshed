"""Provider nodes — one class per supported LLM backend."""

from ..config import get_admin_key, get_api_key, get_config


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
                "context_length": ("INT", {"default": 0, "min": 0, "max": 1048576}),
            },
            "optional": {
                "model_fallback": ("STRING", {"default": "", "defaultInput": True}),
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
        ttl: int,
        context_length: int = 0,
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
                "context_length": context_length if context_length > 0 else None,
            },
        }
        return (provider,)


class LLMProviderOpenAI:
    """OpenAI API provider node. Outputs LLM_PROVIDER dict with oai_compat adapter."""

    RETURN_TYPES = ("LLM_PROVIDER",)
    RETURN_NAMES = ("provider",)
    FUNCTION = "build_provider"
    CATEGORY = "LLM Bikeshed/providers"

    @classmethod
    def INPUT_TYPES(cls) -> dict:
        return {
            "required": {
                "url": ("STRING", {"default": "https://api.openai.com"}),
                "model": (["(refresh to load)"],),
            },
            "optional": {
                "model_fallback": ("STRING", {"default": "", "defaultInput": True}),
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
    ) -> tuple[dict]:
        """Build LLM_PROVIDER dict for OpenAI Chat Completions."""
        fallback = model_fallback.strip() if model_fallback else ""
        resolved_model = fallback if fallback else model

        cfg = get_config()
        timeout = cfg.get("providers", {}).get("openai", {}).get("timeout", 120)
        api_key = get_api_key("openai")

        provider = {
            "backend": "openai",
            "adapter": "oai_compat",
            "url": url.rstrip("/"),
            "model": resolved_model,
            "timeout": timeout,
            "api_key": api_key,
            "admin_key": None,
            "memory": {},
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

    @classmethod
    def VALIDATE_INPUTS(cls, model: str = "", **kwargs: object) -> bool:  # noqa: N802
        """Accept any model string — list is dynamically populated by JS."""
        return True

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


class LLMProviderTextGenWebUI:
    """Textgen (text-generation-webui) provider node.

    Outputs LLM_PROVIDER dict with oai_compat adapter.
    """

    RETURN_TYPES = ("LLM_PROVIDER",)
    RETURN_NAMES = ("provider",)
    FUNCTION = "build_provider"
    CATEGORY = "LLM Bikeshed/providers"

    @classmethod
    def INPUT_TYPES(cls) -> dict:
        return {
            "required": {
                "url": ("STRING", {"default": "http://localhost:5000"}),
                "model": (["(refresh to load)"],),
            },
            "optional": {
                "model_fallback": ("STRING", {"default": "", "defaultInput": True}),
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
    ) -> tuple[dict]:
        """Build LLM_PROVIDER dict for text-gen-webui backend."""
        fallback = model_fallback.strip() if model_fallback else ""
        resolved_model = fallback if fallback else model

        cfg = get_config()
        provider_cfg = cfg.get("providers", {}).get("text_gen_webui", {})
        timeout = provider_cfg.get("timeout", 120)
        api_key = get_api_key("text_gen_webui")
        admin_key = get_admin_key("text_gen_webui")

        provider = {
            "backend": "text_gen_webui",
            "adapter": "oai_compat",
            "url": url.rstrip("/"),
            "model": resolved_model,
            "timeout": timeout,
            "api_key": api_key,
            "admin_key": admin_key,
            "memory": {
                "keep_alive": None,
                "ttl": None,
            },
        }
        return (provider,)
