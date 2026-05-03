"""ComfyUI LLM Bikeshed — local LLM text generation nodes."""

try:
    from .nodes.generation import LLMGenerate, LLMGenerateAdvanced
    from .nodes.lifecycle import LLMLifecycleLMStudio, LLMLifecycleTextGenWebUI
    from .nodes.options_lm_studio import LLMOptionsLMStudio
    from .nodes.options_ollama import LLMOptionsOllamaCore, LLMOptionsOllamaExtra
    from .nodes.options_openai import LLMOptionsOpenAI
    from .nodes.options_text_gen_webui import LLMOptionsTextGenWebUI
    from .nodes.providers import LLMProviderOAICompat, LLMProviderOllama
    from .nodes.utils import LLMLoadTextFile, LLMPresetLoader

    # Import server module to trigger PromptServer endpoint registration
    from .server import endpoints as _endpoints  # noqa: F401

    NODE_CLASS_MAPPINGS = {
        "LLMProviderOAICompat": LLMProviderOAICompat,
        "LLMProviderOllama": LLMProviderOllama,
        "LLMLifecycleLMStudio": LLMLifecycleLMStudio,
        "LLMLifecycleTextGenWebUI": LLMLifecycleTextGenWebUI,
        "LLMGenerate": LLMGenerate,
        "LLMGenerateAdvanced": LLMGenerateAdvanced,
        "LLMOptionsOllamaCore": LLMOptionsOllamaCore,
        "LLMOptionsOllamaExtra": LLMOptionsOllamaExtra,
        "LLMOptionsLMStudio": LLMOptionsLMStudio,
        "LLMOptionsOpenAI": LLMOptionsOpenAI,
        "LLMOptionsTextGenWebUI": LLMOptionsTextGenWebUI,
        "LLMPresetLoader": LLMPresetLoader,
        "LLMLoadTextFile": LLMLoadTextFile,
    }

    NODE_DISPLAY_NAME_MAPPINGS = {
        "LLMProviderOAICompat": "LLM Provider: OAI Compatible",
        "LLMProviderOllama": "LLM Provider: Ollama",
        "LLMLifecycleLMStudio": "LLM Lifecycle: LM Studio",
        "LLMLifecycleTextGenWebUI": "LLM Lifecycle: Textgen",
        "LLMGenerate": "LLM Generate (Basic)",
        "LLMGenerateAdvanced": "LLM Generate (Advanced)",
        "LLMOptionsOllamaCore": "LLM Options: Ollama (Core)",
        "LLMOptionsOllamaExtra": "LLM Options: Ollama (Extra)",
        "LLMOptionsLMStudio": "LLM Options: LM Studio",
        "LLMOptionsOpenAI": "LLM Options: OpenAI",
        "LLMOptionsTextGenWebUI": "LLM Options: Textgen",
        "LLMPresetLoader": "LLM Preset Loader",
        "LLMLoadTextFile": "LLM Load Text File",
    }
except ImportError:
    NODE_CLASS_MAPPINGS = {}
    NODE_DISPLAY_NAME_MAPPINGS = {}

WEB_DIRECTORY = "./js"

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]
