"""ComfyUI LLM Bikeshed — local LLM text generation nodes."""

from nodes.providers import LLMProviderLMStudio
from nodes.generation import LLMGenerate

# Import server module to trigger PromptServer endpoint registration
from server import endpoints as _endpoints  # noqa: F401

NODE_CLASS_MAPPINGS = {
    "LLMProviderLMStudio": LLMProviderLMStudio,
    "LLMGenerate": LLMGenerate,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "LLMProviderLMStudio": "LM Studio Provider",
    "LLMGenerate": "LLM Generate (Basic)",
}

WEB_DIRECTORY = "./js"

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]
