"""Ollama Options nodes — Core (sentinel pattern) and Extra (toggle pattern)."""


class LLMOptionsOllamaCore:
    """Core Ollama generation parameters using sentinel-value pattern.

    Sentinel values (e.g. -1 for ints, -1.0 for floats, "" for strings)
    indicate "use model default" and are excluded from the output dict.
    """

    CATEGORY = "LLM Bikeshed/options"
    RETURN_TYPES = ("LLM_OPTIONS",)
    RETURN_NAMES = ("options",)
    FUNCTION = "build_options"

    SENTINELS = {
        "temperature": -1.0,
        "top_k": -1,
        "top_p": -1.0,
        "seed": -1,
        "num_predict": -1,
        "num_ctx": -1,
        "stop": "",
    }

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "temperature": ("FLOAT", {"default": -1.0, "min": -1.0, "max": 2.0, "step": 0.05}),
                "top_k": ("INT", {"default": -1, "min": -1, "max": 500}),
                "top_p": ("FLOAT", {"default": -1.0, "min": -1.0, "max": 1.0, "step": 0.05}),
                "seed": ("INT", {"default": -1, "min": -1, "max": 2**31 - 1}),
                "num_predict": ("INT", {"default": -1, "min": -1, "max": 128000}),
                "num_ctx": ("INT", {"default": -1, "min": -1, "max": 131072}),
                "stop": ("STRING", {"default": ""}),
            },
            "optional": {
                "options_in": ("LLM_OPTIONS",),
            },
        }

    def build_options(self, options_in: dict = None, **kwargs) -> tuple:
        options = dict(options_in) if options_in else {}
        for param, sentinel in self.SENTINELS.items():
            value = kwargs.get(param)
            if value is not None and value != sentinel:
                options[param] = value
        return (options,)
