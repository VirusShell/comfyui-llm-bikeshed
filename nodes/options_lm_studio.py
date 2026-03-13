"""LM Studio Options node — toggle pattern for OAI-compatible parameters."""


class LLMOptionsLMStudio:
    """LM Studio generation parameters using toggle pattern.

    Each parameter has an ``enable_{name}`` boolean toggle.  Only toggled-on
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
            "default": 2048, "min": 1, "max": 128000,
        }),
        ("seed", "INT", {
            "default": -1, "min": -1, "max": 2**31 - 1,
        }),
        ("stop", "STRING", {"default": ""}),
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
    def INPUT_TYPES(cls):
        inputs = {
            "required": {},
            "optional": {"options_in": ("LLM_OPTIONS",)},
        }
        for name, dtype, opts in cls.PARAMS:
            inputs["optional"][f"enable_{name}"] = (
                "BOOLEAN",
                {"default": False, "label_on": "ON", "label_off": "OFF"},
            )
            inputs["optional"][name] = (dtype, opts)
        return inputs

    def build_options(self, options_in: dict = None, **kwargs) -> tuple:
        options = dict(options_in) if options_in else {}
        for name, _, _ in self.PARAMS:
            if kwargs.get(f"enable_{name}", False):
                options[name] = kwargs[name]
        return (options,)
