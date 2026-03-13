"""Utility nodes for LLM Bikeshed."""

import os

# Directory where preset .txt files are stored
_PRESETS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "presets")


def _list_preset_files() -> list[str]:
    """Return sorted list of .txt filenames in presets/ directory."""
    if not os.path.isdir(_PRESETS_DIR):
        return []
    return sorted(
        f for f in os.listdir(_PRESETS_DIR) if f.endswith(".txt") and f != "README.txt"
    )


class LLMPresetLoader:
    """Load a system prompt preset from the presets/ directory."""

    @classmethod
    def INPUT_TYPES(cls) -> dict:
        files = _list_preset_files()
        if not files:
            files = ["(no presets found)"]
        return {
            "required": {
                "preset": (files, {"default": files[0]}),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("text",)
    FUNCTION = "load_preset"
    CATEGORY = "LLM Bikeshed/utils"

    def load_preset(self, preset: str) -> tuple[str]:
        """Read preset file content and return as string."""
        if preset == "(no presets found)":
            return ("",)
        filepath = os.path.join(_PRESETS_DIR, preset)
        with open(filepath, encoding="utf-8") as f:
            content = f.read()
        return (content,)
