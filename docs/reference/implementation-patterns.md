# Implementation Patterns & Code Examples

> **Last updated:** 2026-03-09
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
            "prompt": "PROMPT",
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


def has_downstream_generation_node(prompt: dict, my_node_id: str, meta_output_index: int,
                                    generation_class_types: set) -> bool:
    """Check if any downstream node on the meta output is a generation node."""
    downstream = find_downstream_nodes(prompt, my_node_id, meta_output_index)
    return any(class_type in generation_class_types for _, class_type, _ in downstream)
```

---

## PromptServer Endpoint (Model List)

```python
from aiohttp import web
from server import PromptServer
import asyncio
import requests

@PromptServer.instance.routes.post("/llm-bikeshed/models")
async def get_models(request):
    data = await request.json()
    backend_type = data.get("backend_type", "ollama")
    url = data.get("url", "http://localhost:11434")
    timeout = data.get("timeout", 10)

    try:
        if backend_type == "ollama":
            response = await asyncio.to_thread(
                requests.get, f"{url}/api/tags", timeout=timeout
            )
            models = [m["name"] for m in response.json().get("models", [])]
        elif backend_type == "lm_studio":
            response = await asyncio.to_thread(
                requests.get, f"{url}/v1/models", timeout=timeout
            )
            models = [m["id"] for m in response.json().get("data", [])]
        elif backend_type == "text_gen_webui":
            headers = {}
            admin_key = data.get("admin_key")
            if admin_key:
                headers["Authorization"] = f"Bearer {admin_key}"
            response = await asyncio.to_thread(
                requests.get, f"{url}/v1/internal/model/list",
                headers=headers, timeout=timeout
            )
            models = response.json().get("model_names", [])
        else:
            models = []

        return web.json_response({"models": models, "error": None})
    except Exception as e:
        return web.json_response({"models": [], "error": str(e)})
```

---

## Frontend JS — Model Dropdown

```javascript
import { app } from "../../scripts/app.js";

app.registerExtension({
    name: "llm-bikeshed.model-dropdown",
    async nodeCreated(node) {
        const providerNodes = [
            "LLMProviderOllama",
            "LLMProviderLMStudio",
            "LLMProviderTextGenWebUI"
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
class LLMOptionsOllama:
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
        param_names = ["temperature", "top_k", "top_p", "seed", "num_predict",
                       "num_ctx", "repeat_penalty", "mirostat", "mirostat_eta",
                       "mirostat_tau", "tfs_z", "min_p", "typical_p"]
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
        f"{url}/api/chat",
        json=payload,
        timeout=timeout,
    )
    response.raise_for_status()

    result = response.json()
    text = result["message"]["content"]
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

- Research findings from `specs/comfyui-llm-bikeshed/research.md`
- ComfyUI custom node research at `D:\ai\tmp\comfyui-custom-nodes-research\`
- Ecosystem analysis of comfyui-ollama and comfyui-ollama-describer
