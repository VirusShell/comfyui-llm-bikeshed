# Implementation Patterns & Code Examples

> **Last updated:** 2026-06-08  
> **Purpose:** Ready-to-use code patterns for implementing the node pack

---

## Custom Type Registration

No registration API needed. Just use uppercase strings consistently:

```python
# provider_node.py
RETURN_TYPES = ("LLM_PROVIDER",)
RETURN_NAMES = ("provider",)

# generation_node.py
@classmethod
def INPUT_TYPES(cls):
    return {
        "required": {
            "provider": ("LLM_PROVIDER",),
            "prompt": ("STRING", {"multiline": True}),
        },
        "optional": {
            "options": ("LLM_OPTIONS",),
            "meta": ("LLM_META",),
            "system_prompt": ("STRING", {"multiline": True, "default": ""}),
        },
        "hidden": {
            # Use a distinct key when a required widget is also named "prompt" (name collision).
            "prompt_graph": "PROMPT",
            "unique_id": "UNIQUE_ID",
        },
    }
```

---

## Graph Topology Introspection (P-10)

```python
def find_downstream_nodes(prompt: dict, my_node_id: str, output_index: int = 0) -> list:
    """Find all nodes whose inputs connect to my_node_id's output_index."""
    downstream = []
    for node_id, node_def in prompt.items():
        for input_name, input_val in node_def.get("inputs", {}).items():
            if isinstance(input_val, list) and len(input_val) == 2:
                if str(input_val[0]) == str(my_node_id) and input_val[1] == output_index:
                    downstream.append((node_id, node_def["class_type"], input_name))
    return downstream


GENERATION_CLASS_TYPES = {"LLMGenerate", "LLMGenerateAdvanced"}  # graph/introspection.py


def has_downstream_gen_node(prompt: dict, node_id: str, meta_output_index: int) -> bool:
    """True if meta output connects to another generation node (unload deferral)."""
    downstream = find_downstream_nodes(prompt, node_id, meta_output_index)
    return any(ct in GENERATION_CLASS_TYPES for _, ct, _ in downstream)
```

---

## PromptServer Endpoint (Model List)

```python
from aiohttp import web
from server import PromptServer
import asyncio
from model_list import (
    _sync_resolve_oai_compat_models,
    _sync_resolve_textgen_models,
)

@PromptServer.instance.routes.post("/llm-bikeshed/models/oai-compat")
async def get_models_oai_compat(request):
    """OAI-compatible model list (LM Studio, OpenAI, generic OAI, etc.)."""
    data = await request.json()
    url = data.get("url", "")
    if not url:
        return web.json_response({"models": [], "backend": "generic"})

    models, backend, loaded_model = await asyncio.to_thread(
        _sync_resolve_oai_compat_models, url,
    )
    payload = {"models": models, "backend": backend}
    if backend == "text_gen_webui":
        payload["loaded_model"] = loaded_model
    return web.json_response(payload)


@PromptServer.instance.routes.post("/llm-bikeshed/models/textgen")
async def get_models_textgen(request):
    """Textgen-only model list (skips multi-backend detection)."""
    data = await request.json()
    url = data.get("url", "")
    if not url:
        return web.json_response(
            {"models": [], "backend": "text_gen_webui", "loaded_model": None},
        )
    models, backend, loaded_model = await asyncio.to_thread(
        _sync_resolve_textgen_models, url,
    )
    return web.json_response(
        {"models": models, "backend": backend, "loaded_model": loaded_model},
    )
```

---

## Frontend JS — Model Dropdown

```javascript
import { app } from "../../scripts/app.js";

app.registerExtension({
    name: "llm-bikeshed.model-dropdown",
    async nodeCreated(node) {
        const providerNodes = [
            "LLMProviderOAICompat",
            "LLMProviderTextGenWebUI",
        ];
        if (!providerNodes.includes(node.comfyClass)) return;

        const modelWidget = node.widgets.find(w => w.name === "model");
        if (!modelWidget) return;

        // Add refresh button behavior
        // Fetch from /llm-bikeshed/models endpoint
        // Update modelWidget.options.values
        // node.setSize(node.computeSize());
    }
});
```

---

## Toggle-Based Options Pattern

```python
class LLMOptionsLMStudio:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {},
            "optional": {
                "enable_temperature": ("BOOLEAN", {"default": False, "label_on": "ON", "label_off": "OFF"}),
                "temperature": ("FLOAT", {"default": 0.8, "min": 0.0, "max": 2.0, "step": 0.05}),
                "enable_top_k": ("BOOLEAN", {"default": False, "label_on": "ON", "label_off": "OFF"}),
                "top_k": ("INT", {"default": 40, "min": 0, "max": 500}),
                # ... more toggle+value pairs
            },
        }
    RETURN_TYPES = ("LLM_OPTIONS",)
    FUNCTION = "build_options"
    CATEGORY = "LLM/config"

    def build_options(self, **kwargs):
        options = {}
        param_names = [
            "temperature", "top_p", "max_tokens", "seed", "stop",
            "top_k", "repeat_penalty", "presence_penalty", "frequency_penalty",
        ]
        for name in param_names:
            if kwargs.get(f"enable_{name}", False):
                options[name] = kwargs[name]
        return (options,)
```

---

## Sync HTTP in FUNCTION Method

```python
import requests
import logging

logger = logging.getLogger("llm-bikeshed")

def generate(self, provider: dict, prompt: str, system_prompt: str = "",
             options: dict = None, **kwargs) -> tuple:
    url = provider["url"]
    model = provider["model"]
    timeout = provider.get("timeout", 120)

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    payload = {"model": model, "messages": messages, "stream": False}

    # Merge options if provided
    if options:
        # Adapter handles parameter name mapping and allowlist filtering
        payload.update(self.adapter.prepare_options(options))

    response = requests.post(
        f"{url}/v1/chat/completions",
        json=payload,
        timeout=timeout,
    )
    response.raise_for_status()

    result = response.json()
    text = result["choices"][0]["message"]["content"]
    return (text,)
```

---

## Config Loading (Merge on Load — I-7)

On startup, `config.example.yaml` (shipped defaults) is deep-merged with the user's `config.yaml`. User values always win. New keys appear with defaults. Neither file is modified on disk.

```python
import copy
import yaml
import os
import logging

logger = logging.getLogger("llm-bikeshed")

_config = None
_pack_dir = os.path.dirname(__file__)
_example_path = os.path.join(_pack_dir, "config.example.yaml")
_user_path = os.path.join(_pack_dir, "config.yaml")


def _deep_merge(base: dict, override: dict) -> dict:
    """Deep-merge override into base. Override values win. Both dicts preserved."""
    result = copy.deepcopy(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def load_config() -> dict:
    """Load config: deep-merge example (defaults) with user config."""
    global _config

    # Load shipped defaults
    if os.path.exists(_example_path):
        with open(_example_path, "r") as f:
            defaults = yaml.safe_load(f) or {}
    else:
        defaults = {}
        logger.warning(f"No config.example.yaml found at {_example_path}")

    # Load user overrides
    if os.path.exists(_user_path):
        with open(_user_path, "r") as f:
            user = yaml.safe_load(f) or {}
        logger.info(f"User config loaded from {_user_path}")
    else:
        user = {}
        logger.info("No config.yaml found, using defaults from config.example.yaml")

    _config = _deep_merge(defaults, user)
    return _config


def get_config() -> dict:
    global _config
    if _config is None:
        load_config()
    return _config


def get_api_key(provider: str) -> str | None:
    """Resolve API key: config.yaml -> env var -> None"""
    config = get_config()
    key = config.get("providers", {}).get(provider, {}).get("api_key")
    if key:
        return key
    env_var = f"LLM_BIKESHED_{provider.upper()}_API_KEY"
    return os.environ.get(env_var)
```

---

## Sources

- Research findings from `specs/comfyui-llm-bikeshed/research.md` (gitignored Ralph spec)
- `docs/reference/comfyui-platform-findings.md` — project-verified platform behavior
- [ComfyUI custom nodes (official docs)](https://docs.comfy.org/custom-nodes/)
- Off-repo Feb 2026 doc mirror — inventory only: `docs/research/external-comfyui-reference-corpus.md`
- Ecosystem analysis of comfyui-ollama and comfyui-ollama-describer
