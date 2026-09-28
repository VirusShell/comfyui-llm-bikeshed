"""Generation nodes for LLM text generation."""

from __future__ import annotations

try:
    from ..adapters import get_adapter
    from ..config.auth import public_provider
    from ..graph.introspection import has_downstream_gen_node
except ImportError:
    from adapters import get_adapter
    from config.auth import public_provider
    from graph.introspection import has_downstream_gen_node


def _build_messages(system_prompt: str, prompt: str) -> list[dict[str, str]]:
    """Build message list for LLM chat completion.

    Args:
        system_prompt: System prompt text. Omitted from messages if empty.
        prompt: User prompt text. Always included.

    Returns:
        List of message dicts with 'role' and 'content' keys.
    """
    messages: list[dict[str, str]] = []
    if system_prompt:
        messages.append({"role": "system", "content": str(system_prompt)})
    messages.append({"role": "user", "content": str(prompt)})
    return messages


# Output cap on the Generate face. 0 is a real value: omit this face limit.
_MAX_TOKENS_INPUT = (
    "INT",
    {
        "default": 1024,
        "min": 0,
        "max": 128000,
        "tooltip": (
            "Output token cap only (not prompt + completion). "
            "0 omits this face limit so the host default applies; "
            "an Options or meta limit is kept. "
            "1 or more is sent. No prompt cap; you own timeout and OOM."
        ),
    },
)

_UNLOAD_ON_INTERRUPT_PROPERTY = "unload_on_interrupt"


def _apply_face_max_tokens(
    options: dict, max_tokens: int, backend: str | None
) -> None:
    """Apply the Generate-face output cap.

    Values below 1 do not write a face limit (host default, unless Options
    or meta already set one). 1 or more sends that many completion tokens:
    ``max_completion_tokens`` for OpenAI, ``max_tokens`` for legacy hosts.
    """
    if int(max_tokens) < 1:
        return
    limit = int(max_tokens)
    if backend == "openai":
        options["max_completion_tokens"] = limit
        options.pop("max_tokens", None)
    else:
        options["max_tokens"] = limit


def _provider_backend(provider: dict | None) -> str | None:
    if not isinstance(provider, dict):
        return None
    backend = provider.get("backend")
    if backend is None or backend == "":
        return None
    return str(backend)


def _coerce_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return False


def unload_on_interrupt_enabled(extra_pnginfo: object, unique_id: object) -> bool:
    """Read Generate node property ``unload_on_interrupt`` (default off).

    ComfyUI keeps LiteGraph properties on the workflow node and passes them
    at queue time as ``extra_pnginfo["workflow"]["nodes"]``. Prompts that
    omit that blob keep the default: do not unload on interrupt.
    """
    if not isinstance(extra_pnginfo, dict):
        return False
    workflow = extra_pnginfo.get("workflow")
    if not isinstance(workflow, dict):
        return False
    nodes = workflow.get("nodes")
    if not isinstance(nodes, list):
        return False
    uid = str(unique_id)
    for node in nodes:
        if not isinstance(node, dict) or str(node.get("id")) != uid:
            continue
        props = node.get("properties")
        if not isinstance(props, dict):
            return False
        if _UNLOAD_ON_INTERRUPT_PROPERTY not in props:
            return False
        return _coerce_bool(props[_UNLOAD_ON_INTERRUPT_PROPERTY])
    return False


class LLMGenerate:
    """Basic Generation node — compact, all-in-one with inline params."""

    CATEGORY = "LLM Bikeshed/generation"
    RETURN_TYPES = ("STRING", "LLM_META")
    RETURN_NAMES = ("text", "meta")
    OUTPUT_TOOLTIPS = (
        "",
        "Carries provider + options for chaining to downstream generation nodes.",
    )
    FUNCTION = "generate"
    OUTPUT_NODE = False

    @classmethod
    def INPUT_TYPES(cls) -> dict:  # noqa: N802
        return {
            "required": {
                "provider": ("LLM_PROVIDER",),
                "temperature": (
                    "FLOAT",
                    {"default": 0.7, "min": 0.0, "max": 2.0, "step": 0.05},
                ),
                "max_tokens": _MAX_TOKENS_INPUT,
                "seed": (
                    "INT",
                    {
                        "default": 0,
                        "min": 0,
                        "max": 0xffffffffffffffff,
                        "control_after_generate": True,
                    },
                ),
                "system_prompt": ("STRING", {"multiline": True, "default": ""}),
                "prompt": ("STRING", {"multiline": True}),
            },
            "hidden": {
                "prompt_graph": "PROMPT",
                "unique_id": "UNIQUE_ID",
                "extra_pnginfo": "EXTRA_PNGINFO",
            },
        }

    @classmethod
    def IS_CHANGED(cls, **kwargs: object) -> float:  # noqa: N802
        """Always-rerun fingerprint (deliberate).

        Returning float("NaN") makes ComfyUI treat every queue as changed so LLM
        HTTP calls are not skipped by the cache. Do not replace with a stable
        hash unless product wants cached generate skips. See CODEBASE.md.
        """
        return float("NaN")

    @classmethod
    def VALIDATE_INPUTS(cls, **kwargs: object) -> bool:  # noqa: N802
        """Validate inputs before execution.

        Connection values (like provider) aren't available at validation time,
        so we return True to allow execution to proceed.
        """
        return True

    def generate(
        self,
        provider: dict,
        temperature: float,
        max_tokens: int,
        seed: int,
        system_prompt: str,
        prompt: str,
        **kwargs: object,
    ) -> tuple[str, dict]:
        """Run LLM generation and return (text, meta)."""
        # Build inline options — 0 max_tokens omits the face cap (host default).
        options: dict = {}
        if temperature >= 0:
            options["temperature"] = temperature
        _apply_face_max_tokens(options, max_tokens, _provider_backend(provider))
        options["seed"] = seed

        adapter = get_adapter(provider["adapter"])

        # Hidden inputs come through kwargs (name collision with required 'prompt')
        prompt_graph = kwargs.get("prompt_graph", {})
        unique_id = kwargs.get("unique_id")

        # Check if downstream gen node exists (meta output is index 1)
        skip_unload = has_downstream_gen_node(prompt_graph, unique_id, 1)
        unload_on_interrupt = unload_on_interrupt_enabled(
            kwargs.get("extra_pnginfo"), unique_id
        )

        messages = _build_messages(system_prompt, prompt)
        text = adapter.generate(
            provider,
            messages,
            options,
            skip_unload,
            unload_on_interrupt=unload_on_interrupt,
        )

        meta: dict = {"provider": public_provider(provider), "options": options}
        return (text, meta)


class LLMGenerateAdvanced:
    """Intended Generate spine — Advanced shape plus an output-token knob.

    ``max_tokens`` sits above ``seed``. Optional provider / options / meta
    stay. Basic stays registered; this class is not a rename.
    """

    CATEGORY = "LLM Bikeshed/generation"
    RETURN_TYPES = ("STRING", "LLM_META")
    RETURN_NAMES = ("text", "meta")
    OUTPUT_TOOLTIPS = (
        "",
        "Carries provider + options for chaining to downstream generation nodes.",
    )
    FUNCTION = "generate"
    OUTPUT_NODE = False

    @classmethod
    def INPUT_TYPES(cls) -> dict:  # noqa: N802
        return {
            "required": {
                "system_prompt": ("STRING", {"multiline": True, "default": ""}),
                "prompt": ("STRING", {"multiline": True}),
                "max_tokens": _MAX_TOKENS_INPUT,
                "seed": (
                    "INT",
                    {
                        "default": 0,
                        "min": 0,
                        "max": 0xffffffffffffffff,
                        "control_after_generate": True,
                    },
                ),
            },
            "optional": {
                "provider": ("LLM_PROVIDER",),
                "options": ("LLM_OPTIONS",),
                "meta": (
                    "LLM_META",
                    {
                        "tooltip": (
                            "Accepts provider + options from an upstream "
                            "generation node. Explicit provider/options inputs "
                            "override meta values."
                        ),
                    },
                ),
            },
            "hidden": {
                "prompt_graph": "PROMPT",
                "unique_id": "UNIQUE_ID",
                "extra_pnginfo": "EXTRA_PNGINFO",
            },
        }

    @classmethod
    def IS_CHANGED(cls, **kwargs: object) -> float:  # noqa: N802
        """Always-rerun fingerprint (deliberate).

        Returning float("NaN") makes ComfyUI treat every queue as changed so LLM
        HTTP calls are not skipped by the cache. Do not replace with a stable
        hash unless product wants cached generate skips. See CODEBASE.md.
        """
        return float("NaN")

    @classmethod
    def VALIDATE_INPUTS(cls, **kwargs: object) -> bool:  # noqa: N802
        return True

    def generate(
        self,
        system_prompt: str,
        prompt: str,
        max_tokens: int = 0,
        seed: int = 0,
        provider: dict | None = None,
        options: dict | None = None,
        meta: dict | None = None,
        **kwargs: object,
    ) -> tuple[str, dict]:
        """Run LLM generation with provider/options from explicit inputs or meta."""
        # Meta precedence: explicit inputs win over meta values
        resolved_provider = provider or (meta.get("provider") if meta else None)
        if resolved_provider is None:
            raise ValueError(
                "No provider configured. Connect a Provider node or a meta input."
            )

        resolved_options = dict(
            options or (meta.get("options") if meta else None) or {}
        )
        # Face 0 leaves Options/meta token limits alone. Face >= 1 wins.
        _apply_face_max_tokens(
            resolved_options, max_tokens, _provider_backend(resolved_provider)
        )
        resolved_options["seed"] = seed

        adapter = get_adapter(resolved_provider["adapter"])

        # Hidden inputs come through kwargs (name collision with required 'prompt')
        prompt_graph = kwargs.get("prompt_graph", {})
        unique_id = kwargs.get("unique_id")

        # Check if downstream gen node exists (meta output is index 1)
        skip_unload = has_downstream_gen_node(prompt_graph, unique_id, 1)
        unload_on_interrupt = unload_on_interrupt_enabled(
            kwargs.get("extra_pnginfo"), unique_id
        )

        messages = _build_messages(system_prompt, prompt)
        text = adapter.generate(
            resolved_provider,
            messages,
            resolved_options,
            skip_unload,
            unload_on_interrupt=unload_on_interrupt,
        )

        meta_out: dict = {
            "provider": public_provider(resolved_provider),
            "options": resolved_options,
        }
        return (text, meta_out)
