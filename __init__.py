"""ComfyUI LLM Bikeshed — local LLM text generation nodes."""

from .nodes.generation import LLMGenerate, LLMGenerateAdvanced, LLMGenerateTest
from .nodes.options_lm_studio import LLMOptionsLMStudio
from .nodes.options_lm_studio_test import LLMOptionsLMStudioTest
from .nodes.options_ollama import LLMOptionsOllamaCore, LLMOptionsOllamaExtra
from .nodes.options_openai import LLMOptionsOpenAI
from .nodes.options_text_gen_webui import LLMOptionsTextGenWebUI
from .nodes.providers import (
    LLMProviderLMStudio,
    LLMProviderOllama,
    LLMProviderOpenAI,
    LLMProviderTextGenWebUI,
)
from .nodes.utils import LLMLoadTextFile, LLMPresetLoader

# Import server module to trigger PromptServer endpoint registration
from .server import endpoints as _endpoints  # noqa: F401

NODE_CLASS_MAPPINGS = {
    "LLMProviderLMStudio": LLMProviderLMStudio,
    "LLMProviderOllama": LLMProviderOllama,
    "LLMProviderOpenAI": LLMProviderOpenAI,
    "LLMProviderTextGenWebUI": LLMProviderTextGenWebUI,
    "LLMGenerate": LLMGenerate,
    "LLMGenerateAdvanced": LLMGenerateAdvanced,
    "LLMOptionsOllamaCore": LLMOptionsOllamaCore,
    "LLMOptionsOllamaExtra": LLMOptionsOllamaExtra,
    "LLMOptionsLMStudio": LLMOptionsLMStudio,
    "LLMOptionsOpenAI": LLMOptionsOpenAI,
    "LLMOptionsTextGenWebUI": LLMOptionsTextGenWebUI,
    "LLMGenerateTest": LLMGenerateTest,
    "LLMOptionsLMStudioTest": LLMOptionsLMStudioTest,
    "LLMPresetLoader": LLMPresetLoader,
    "LLMLoadTextFile": LLMLoadTextFile,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "LLMProviderLMStudio": "LLM Provider: LM Studio",
    "LLMProviderOllama": "LLM Provider: Ollama",
    "LLMProviderOpenAI": "LLM Provider: OpenAI",
    "LLMProviderTextGenWebUI": "LLM Provider: Textgen",
    "LLMGenerate": "LLM Generate (Basic)",
    "LLMGenerateAdvanced": "LLM Generate (Advanced)",
    "LLMOptionsOllamaCore": "LLM Options: Ollama (Core)",
    "LLMOptionsOllamaExtra": "LLM Options: Ollama (Extra)",
    "LLMOptionsLMStudio": "LLM Options: LM Studio",
    "LLMOptionsOpenAI": "LLM Options: OpenAI",
    "LLMOptionsTextGenWebUI": "LLM Options: Textgen",
    "LLMGenerateTest": "LLM Generate (test)",
    "LLMOptionsLMStudioTest": "LLM Options: LM Studio (test)",
    "LLMPresetLoader": "LLM Preset Loader",
    "LLMLoadTextFile": "LLM Load Text File",
}

WEB_DIRECTORY = "./js"

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]
