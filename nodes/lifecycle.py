"""Lifecycle nodes — optional VRAM management for LM Studio and Textgen."""

from __future__ import annotations


class LLMLifecycleLMStudio:
    """LM Studio VRAM lifecycle — TTL and optional context_length override."""

    RETURN_TYPES = ("LLM_LIFECYCLE",)
    RETURN_NAMES = ("lifecycle",)
    OUTPUT_TOOLTIPS = (
        "Connect to the lifecycle input on LLM Provider: OAI Compatible when the "
        "detected backend is LM Studio.",
    )
    FUNCTION = "build_lifecycle"
    CATEGORY = "LLM Bikeshed/lifecycle"
    DESCRIPTION = (
        "Optional VRAM management for LM Studio when using LLM Provider: OAI "
        "Compatible. Connect lifecycle to the provider's lifecycle input. The "
        "adapter applies TTL on each chat request and can load the model with an "
        "explicit context length before generation."
    )

    @classmethod
    def INPUT_TYPES(cls) -> dict:  # noqa: N802
        return {
            "required": {
                "ttl": (
                    "INT",
                    {
                        "default": 30,
                        "min": 0,
                        "tooltip": (
                            "Time-to-live in seconds — how long LM Studio keeps "
                            "the model loaded after each request. Timer resets "
                            "on each request. 0 = unload immediately."
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
                            "Context window for explicit model load via LM Studio "
                            "REST API. 0 = use the model default."
                        ),
                    },
                ),
            },
        }

    def build_lifecycle(
        self, ttl: int, context_length: int = 0
    ) -> tuple[dict]:
        """Build LLM_LIFECYCLE dict for LM Studio VRAM management."""
        return (
            {
                "type": "lm_studio",
                "ttl": ttl,
                "context_length": context_length if context_length > 0 else None,
            },
        )


class LLMLifecycleTextGenWebUI:
    """Textgen VRAM lifecycle — presence enables load/unload management.

    ComfyUI does not reliably render nodes whose ``INPUT_TYPES`` has no widgets
    (only title + output). A BOOLEAN widget keeps the node usable while staying
    optional to disable by returning an empty lifecycle dict.
    """

    RETURN_TYPES = ("LLM_LIFECYCLE",)
    RETURN_NAMES = ("lifecycle",)
    OUTPUT_TOOLTIPS = (
        "Connect to the lifecycle input on LLM Provider: OAI Compatible when "
        "the detected backend is Textgen.",
    )
    FUNCTION = "build_lifecycle"
    CATEGORY = "LLM Bikeshed/lifecycle"
    DESCRIPTION = (
        "Optional VRAM management for Textgen (text-generation-webui) when using "
        "LLM Provider: OAI Compatible. Turn Manage model memory ON to load before "
        "chat and unload after the last generation in a chain. For new workflows, "
        "prefer LLM Provider: Textgen with Manage model memory ON instead of this "
        "node."
    )

    @classmethod
    def INPUT_TYPES(cls) -> dict:  # noqa: N802
        return {
            "required": {
                "manage_model_memory": (
                    "BOOLEAN",
                    {
                        "default": True,
                        "label_on": "ON",
                        "label_off": "OFF",
                        "tooltip": (
                            "When ON, load the selected model before generation and "
                            "unload after the last node in a chain. OFF = same as "
                            "leaving lifecycle disconnected."
                        ),
                    },
                ),
            },
        }

    def build_lifecycle(self, manage_model_memory: bool) -> tuple[dict]:
        """Build LLM_LIFECYCLE dict for Textgen VRAM management."""
        if not manage_model_memory:
            # Empty dict is falsy — adapter skips load/unload (same as no lifecycle).
            return ({},)

        return (
            {
                "type": "text_gen_webui",
            },
        )
