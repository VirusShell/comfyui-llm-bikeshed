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
    """Textgen VRAM lifecycle — presence enables load/unload management."""

    RETURN_TYPES = ("LLM_LIFECYCLE",)
    RETURN_NAMES = ("lifecycle",)
    FUNCTION = "build_lifecycle"
    CATEGORY = "LLM Bikeshed/lifecycle"

    @classmethod
    def INPUT_TYPES(cls) -> dict:  # noqa: N802
        return {
            "required": {},
        }

    def build_lifecycle(self) -> tuple[dict]:
        """Build LLM_LIFECYCLE dict for Textgen VRAM management."""
        return (
            {
                "type": "text_gen_webui",
            },
        )
