"""ComfyUI LLM Bikeshed — local LLM text generation nodes."""

try:
    from .nodes.generation import LLMGenerate, LLMGenerateAdvanced
    from .nodes.lifecycle import LLMLifecycleLMStudio, LLMLifecycleTextGenWebUI
    from .nodes.options_lm_studio import LLMOptionsLMStudio
    from .nodes.options_openai import LLMOptionsOpenAI
    from .nodes.options_text_gen_webui import LLMOptionsTextGenWebUI
    from .nodes.providers import LLMProviderOAICompat, LLMProviderTextGenWebUI
    from .nodes.utils import LLMLoadTextFile, LLMPresetLoader

    # Import server module to trigger PromptServer endpoint registration
    from .server import endpoints as _endpoints  # noqa: F401

    NODE_CLASS_MAPPINGS = {
        "LLMProviderOAICompat": LLMProviderOAICompat,
        "LLMProviderTextGenWebUI": LLMProviderTextGenWebUI,
        "LLMLifecycleLMStudio": LLMLifecycleLMStudio,
        "LLMLifecycleTextGenWebUI": LLMLifecycleTextGenWebUI,
        "LLMGenerate": LLMGenerate,
        "LLMGenerateAdvanced": LLMGenerateAdvanced,
        "LLMOptionsLMStudio": LLMOptionsLMStudio,
        "LLMOptionsOpenAI": LLMOptionsOpenAI,
        "LLMOptionsTextGenWebUI": LLMOptionsTextGenWebUI,
        "LLMPresetLoader": LLMPresetLoader,
        "LLMLoadTextFile": LLMLoadTextFile,
    }

    NODE_DISPLAY_NAME_MAPPINGS = {
        "LLMProviderOAICompat": "LLM Provider: OAI Compatible",
        "LLMProviderTextGenWebUI": "LLM Provider: Textgen",
        "LLMLifecycleLMStudio": "LLM Lifecycle: LM Studio",
        "LLMLifecycleTextGenWebUI": "LLM Lifecycle: Textgen",
        "LLMGenerate": "LLM Generate (Basic)",
        "LLMGenerateAdvanced": "LLM Generate (Advanced)",
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
