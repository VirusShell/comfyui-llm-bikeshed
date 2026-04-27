"""LM Studio Options (test) node — stripped-down toggle pattern."""

from __future__ import annotations

from .options_base import build_toggle_options


class LLMOptionsLMStudioTest:
    """LM Studio test options — no temperature, max_tokens, seed, or control."""

    CATEGORY = "LLM Bikeshed/options"
    RETURN_TYPES = ("LLM_OPTIONS",)
    RETURN_NAMES = ("options",)
    FUNCTION = "build_options"

    PARAMS = [
        ("top_p", "FLOAT", {
            "default": 1.0, "min": 0.0,
            "max": 1.0, "step": 0.05,
        }),
        ("stop_string", "STRING", {"default": ""}),
        ("top_k", "INT", {
            "default": 40, "min": 0, "max": 500,
        }),
        ("repeat_penalty", "FLOAT", {
            "default": 1.1, "min": 0.0,
            "max": 5.0, "step": 0.05,
        }),
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
