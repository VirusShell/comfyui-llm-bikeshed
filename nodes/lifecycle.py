"""Lifecycle nodes — optional VRAM management for LM Studio and Textgen."""

from __future__ import annotations


class LLMLifecycleLMStudio:
    """LM Studio VRAM lifecycle — TTL and optional context_length override."""

    RETURN_TYPES = ("LLM_LIFECYCLE",)
    RETURN_NAMES = ("lifecycle",)
    FUNCTION = "build_lifecycle"
    CATEGORY = "LLM Bikeshed/lifecycle"

    @classmethod
    def INPUT_TYPES(cls) -> dict:  # noqa: N802
        return {
            "required": {
                "ttl": ("INT", {"default": 30, "min": 0}),
                "context_length": (
                    "INT",
                    {"default": 0, "min": 0, "max": 1048576},
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
    FUNCTION = "build_lifecycle"
    CATEGORY = "LLM Bikeshed/lifecycle"

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
