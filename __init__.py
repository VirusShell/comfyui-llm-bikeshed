"""ComfyUI LLM Bikeshed — local LLM text generation nodes."""

from nodes.generation import LLMGenerate, LLMGenerateAdvanced
from nodes.options_lm_studio import LLMOptionsLMStudio
from nodes.options_ollama import LLMOptionsOllamaCore, LLMOptionsOllamaExtra
from nodes.options_text_gen_webui import LLMOptionsTextGenWebUI
from nodes.providers import (
    LLMProviderLMStudio,
    LLMProviderOllama,
    LLMProviderTextGenWebUI,
)
from nodes.utils import LLMLoadTextFile, LLMPresetLoader

# Import server module to trigger PromptServer endpoint registration
from server import endpoints as _endpoints  # noqa: F401

NODE_CLASS_MAPPINGS = {
    "LLMProviderLMStudio": LLMProviderLMStudio,
    "LLMProviderOllama": LLMProviderOllama,
    "LLMProviderTextGenWebUI": LLMProviderTextGenWebUI,
    "LLMGenerate": LLMGenerate,
    "LLMGenerateAdvanced": LLMGenerateAdvanced,
    "LLMOptionsOllamaCore": LLMOptionsOllamaCore,
    "LLMOptionsOllamaExtra": LLMOptionsOllamaExtra,
    "LLMOptionsLMStudio": LLMOptionsLMStudio,
    "LLMOptionsTextGenWebUI": LLMOptionsTextGenWebUI,
    "LLMPresetLoader": LLMPresetLoader,
    "LLMLoadTextFile": LLMLoadTextFile,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "LLMProviderLMStudio": "LM Studio Provider",
    "LLMProviderOllama": "Ollama Provider",
    "LLMProviderTextGenWebUI": "text-gen-webui Provider",
    "LLMGenerate": "LLM Generate (Basic)",
    "LLMGenerateAdvanced": "LLM Generate (Advanced)",
    "LLMOptionsOllamaCore": "Ollama Options (Core)",
    "LLMOptionsOllamaExtra": "Ollama Options (Extra)",
    "LLMOptionsLMStudio": "LM Studio Options",
    "LLMOptionsTextGenWebUI": "text-gen-webui Options",
    "LLMPresetLoader": "LLM Preset Loader",
    "LLMLoadTextFile": "LLM Load Text File",
}

WEB_DIRECTORY = "./js"

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]
