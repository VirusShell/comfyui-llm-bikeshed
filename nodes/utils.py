"""Utility nodes for LLM Bikeshed."""

import os

try:
    import folder_paths

    _INPUT_DIR = folder_paths.get_input_directory()
except ImportError:
    _INPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "input")

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
        safe_name = os.path.basename(preset)
        filepath = os.path.join(_PRESETS_DIR, safe_name)
        if os.path.commonpath([filepath, _PRESETS_DIR]) != _PRESETS_DIR:
            raise ValueError(f"Invalid preset path: {preset!r}")
        with open(filepath, encoding="utf-8") as f:
            content = f.read()
        return (content,)


def _list_text_files() -> list[str]:
    """Return sorted list of .txt filenames in ComfyUI input directory."""
    if not os.path.isdir(_INPUT_DIR):
        return []
    return sorted(f for f in os.listdir(_INPUT_DIR) if f.endswith(".txt"))


class LLMLoadTextFile:
    """Load a text file from ComfyUI's input directory."""

    @classmethod
    def INPUT_TYPES(cls) -> dict:
        files = _list_text_files()
        if not files:
            files = ["(no .txt files found)"]
        return {
            "required": {
                "file": (files, {"default": files[0]}),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("text",)
    FUNCTION = "load_file"
    CATEGORY = "LLM Bikeshed/utils"

    def load_file(self, file: str) -> tuple[str]:
        """Read text file content and return as string."""
        if file == "(no .txt files found)":
            return ("",)
        safe_name = os.path.basename(file)
        filepath = os.path.join(_INPUT_DIR, safe_name)
        if os.path.commonpath([filepath, _INPUT_DIR]) != _INPUT_DIR:
            raise ValueError(f"Invalid file path: {file!r}")
        with open(filepath, encoding="utf-8") as f:
            content = f.read()
        return (content,)
