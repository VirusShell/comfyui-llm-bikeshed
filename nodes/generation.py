"""Generation nodes for LLM text generation."""

from __future__ import annotations

from adapters import get_adapter
from graph.introspection import has_downstream_gen_node


def _build_messages(system_prompt: str, prompt: str) -> list[dict]:
    """Build message list for LLM chat completion.

    Args:
        system_prompt: System prompt text. Omitted from messages if empty.
        prompt: User prompt text. Always included.

    Returns:
        List of message dicts with 'role' and 'content' keys.
    """
    messages: list[dict] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    return messages


class LLMGenerate:
    """Basic Generation node — compact, all-in-one with inline params."""

    CATEGORY = "LLM Bikeshed/generation"
    RETURN_TYPES = ("STRING", "LLM_META")
    RETURN_NAMES = ("text", "meta")
    FUNCTION = "generate"
    OUTPUT_NODE = False

    @classmethod
    def INPUT_TYPES(cls) -> dict:  # noqa: N802
        return {
            "required": {
                "provider": ("LLM_PROVIDER",),
                "prompt": ("STRING", {"multiline": True}),
            },
            "optional": {
                "system_prompt": ("STRING", {"multiline": True}),
                "temperature": (
                    "FLOAT",
                    {"default": 0.7, "min": 0.0, "max": 2.0, "step": 0.05},
                ),
                "max_tokens": ("INT", {"default": 1024, "min": 1, "max": 128000}),
                "seed": ("INT", {"default": -1}),
            },
            "hidden": {
                "prompt": "PROMPT",
                "unique_id": "UNIQUE_ID",
            },
        }

    @classmethod
    def IS_CHANGED(cls, **kwargs: object) -> float:  # noqa: N802
        return float("NaN")

    def generate(
        self,
        provider: dict,
        prompt: str,
        system_prompt: str = "",
        temperature: float = 0.7,
        max_tokens: int = 1024,
        seed: int = -1,
        **kwargs: object,
    ) -> tuple:
        """Run LLM generation and return (text, meta)."""
        # Build inline options — always include temperature and max_tokens
        options: dict = {
            "temperature": temperature,
            "max_tokens": max_tokens,
            "seed": seed,
        }

        adapter = get_adapter(provider["adapter"])

        # Hidden inputs come through kwargs (name collision with required 'prompt')
        prompt_graph = kwargs.get("prompt", {})
        unique_id = kwargs.get("unique_id")

        # Check if downstream gen node exists (meta output is index 1)
        skip_unload = has_downstream_gen_node(prompt_graph, unique_id, 1)

        messages = _build_messages(system_prompt, prompt)
        text = adapter.generate(provider, messages, options, skip_unload)

        meta: dict = {"provider": provider, "options": options}
        return (text, meta)
