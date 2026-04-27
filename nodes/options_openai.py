"""OpenAI Options node — toggle pattern for core Chat Completions parameters."""

from __future__ import annotations

from .options_base import build_toggle_options


class LLMOptionsOpenAI:
    """OpenAI API generation parameters using toggle pattern.

    Each parameter has an ``enable_{name}`` boolean toggle. Only toggled-on
    parameters are included in the output dict.
    """

    CATEGORY = "LLM Bikeshed/options"
    RETURN_TYPES = ("LLM_OPTIONS",)
    RETURN_NAMES = ("options",)
    FUNCTION = "build_options"

    PARAMS = [
        ("temperature", "FLOAT", {
            "default": 0.7, "min": 0.0,
            "max": 2.0, "step": 0.05,
        }),
        ("top_p", "FLOAT", {
            "default": 1.0, "min": 0.0,
            "max": 1.0, "step": 0.05,
        }),
        ("max_tokens", "INT", {
            "default": 1024, "min": 1, "max": 128000,
        }),
        ("max_completion_tokens", "INT", {
            "default": 1024, "min": 1, "max": 128000,
        }),
        ("seed", "INT", {
            "default": -1, "min": -1, "max": 2**31 - 1,
        }),
        ("stop_string", "STRING", {"default": ""}),
        ("presence_penalty", "FLOAT", {
            "default": 0.0, "min": -2.0,
            "max": 2.0, "step": 0.05,
        }),
        ("frequency_penalty", "FLOAT", {
            "default": 0.0, "min": -2.0,
            "max": 2.0, "step": 0.05,
        }),
    ]

    @classmethod
    def INPUT_TYPES(cls) -> dict:  # noqa: N802
        inputs: dict = {
            "required": {},
            "optional": {},
        }
        for name, dtype, opts in cls.PARAMS:
            inputs["optional"][f"enable_{name}"] = (
                "BOOLEAN",
                {"default": False, "label_on": "ON", "label_off": "OFF"},
            )
            inputs["optional"][name] = (dtype, opts)
        return inputs

    def build_options(self, **kwargs: object) -> tuple[dict]:
        return build_toggle_options(self.PARAMS, kwargs)
