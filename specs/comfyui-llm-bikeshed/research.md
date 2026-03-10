---
spec: comfyui-llm-bikeshed
phase: research
created: 2026-03-09
---

# Research: comfyui-llm-bikeshed

## Executive Summary

ComfyUI's PROMPT hidden input contains the full execution graph with input connections, enabling reverse-indexing to determine downstream connections (P-10). Per-backend API research confirms the three-backend scope is viable with clear parameter mappings. The `requests`-based synchronous HTTP pattern is confirmed standard for ComfyUI nodes. Boolean toggles, COMBO widgets, and custom types all work as expected with minor caveats documented below.

---

## 1. ComfyUI Platform Capabilities

### P-10: Graph Topology Introspection (HIGHEST PRIORITY)

**Status: Confirmed feasible via reverse-indexing PROMPT**

The `PROMPT` hidden input provides the complete execution graph as a dict keyed by node ID. Each node entry contains `class_type` and `inputs`. Input connections use the format `[source_node_id, output_index]`.

**Critical finding:** PROMPT does NOT directly tell a node what its outputs connect to. It only shows what each node's *inputs* come from. However, a node CAN reverse-index the graph at execution time to determine downstream connections.

**Implementation approach:**

```python
def find_downstream_nodes(prompt, my_node_id, output_index=0):
    """Find all nodes whose inputs connect to my_node_id's output_index."""
    downstream = []
    for node_id, node_def in prompt.items():
        for input_name, input_val in node_def.get("inputs", {}).items():
            if isinstance(input_val, list) and len(input_val) == 2:
                if str(input_val[0]) == str(my_node_id) and input_val[1] == output_index:
                    downstream.append((node_id, node_def["class_type"], input_name))
    return downstream
```

To use this, a generation node declares `"hidden": {"prompt": "PROMPT", "unique_id": "UNIQUE_ID"}` and calls the above in its FUNCTION method. It can then check if any downstream node on the `meta` output is another generation node, and skip the unload call if so.

**Confidence: Confirmed** -- PROMPT data structure is documented and the reverse-indexing logic is straightforward Python. The only caveat is that `DYNPROMPT` may differ from `PROMPT` if Node Expansion is used, but our nodes do not use expansion.

**Impact on A-15 (unload deferral):** This is the clean approach. For text-gen-webui's explicit unload: only the last generation node in a meta-chain fires the unload call. For Ollama/LM Studio, this is less critical since keep_alive/ttl timers reset on each request naturally.

Sources:
- [ComfyUI Hidden Inputs docs](https://docs.comfy.org/custom-nodes/backend/more_on_inputs)
- [Workflow JSON Format (DeepWiki)](https://deepwiki.com/Comfy-Org/ComfyUI/7.3-workflow-json-format)

### P-9: Boolean Toggle Widget Save/Load Reliability

**Status: Confirmed reliable**

BOOLEAN is a first-class primitive type in ComfyUI with `default`, `label_on`, `label_off` parameters. It serializes to `widgets_values` like all other widget types. No known save/load issues in the documentation or ecosystem reports.

```python
"enable_temperature": ("BOOLEAN", {"default": False, "label_on": "ON", "label_off": "OFF"})
```

This unblocks the per-parameter enable/disable toggle approach for Options nodes (A-3).

**Confidence: Confirmed** -- documented primitive type with standard serialization.

Source: [ComfyUI Data Types](https://docs.comfy.org/custom-nodes/backend/datatypes)

### P-2/P-3: Dynamic COMBO Behavior and Offline Fallback

**Status: Likely workable with caveats**

**COMBO behavior:** Defined as `list[str]` in `INPUT_TYPES`. Since `INPUT_TYPES` is a classmethod called at registration time (and can be called dynamically), model lists can be populated by querying the backend.

**Offline scenario:** If the backend is unreachable when `INPUT_TYPES` is called, the COMBO list would be empty or contain only a fallback entry. A saved workflow with a model name not in the current list will show a mismatch.

**Recommended approach:** Use a COMBO widget populated via frontend JS rather than backend `INPUT_TYPES`. The JS extension fetches model lists from a custom PromptServer endpoint and updates the widget. This way:
1. The COMBO can show a "Loading..." or "Backend offline" state
2. The saved model name persists in `widgets_values` regardless of current backend state
3. A refresh button can re-query the backend

This is exactly how comfyui-ollama implements model selection: a POST endpoint (`/ollama/get_models`) queries the running backend, and JS populates the dropdown.

**Alternative fallback (P-3):** Instead of COMBO-to-text switching (complex, fragile), use a STRING input with `defaultInput: True`. User can type a model name manually or connect it from another node. The COMBO dropdown exists as a convenience populated by JS, not as the authoritative input mechanism.

**Confidence: Likely** -- follows established ecosystem patterns (comfyui-ollama does this). The COMBO-to-text dynamic switching is unverified and probably unnecessary.

Sources:
- [ComfyUI-Ollama architecture (DeepWiki)](https://deepwiki.com/stavsap/comfyui-ollama/1-overview)
- [ComfyUI JS Extensions docs](https://docs.comfy.org/custom-nodes/js/javascript_overview)

### A-6: Preset File-Loading Mechanism

**Status: Feasible via JS, simpler alternative recommended**

**Option 1 (JS-driven):** A COMBO widget listing preset names, plus a STRING multiline widget for system_prompt. JS `nodeCreated` hook adds a callback on COMBO change that reads the preset text and sets the STRING widget value. The STRING widget is always the authoritative value sent to the backend.

Caveats:
- On workflow load, `loadedGraphNode` fires after `nodeCreated`. Widget values are restored from `widgets_values`. If the preset COMBO triggers its callback during load, it could overwrite the saved system_prompt text. Solution: guard the callback with a flag set during `onConfigure`/`loadedGraphNode`.
- Preset text files can be read via a custom PromptServer endpoint or bundled as JS data.

**Option 2 (Separate node, simpler):** A "Preset Loader" node with a COMBO listing `.txt` files from the node pack's `presets/` directory. Output is STRING, connected to system_prompt input. This is the known-working pattern and avoids all JS widget interaction complexity.

**Recommendation:** Start with Option 2 (separate Preset Loader node). It works without any JS and follows ComfyUI's standard data flow patterns. The inline COMBO approach (Option 1) can be added later as a UX enhancement.

**Confidence: Likely** for Option 1, **Confirmed** for Option 2.

### P-4: Error Display Mechanisms

**Status: Confirmed multiple mechanisms**

1. **Exception in FUNCTION method:** Halts the workflow. ComfyUI shows an error notification in the UI with the exception message. The node gets a red outline. This is the decided approach (I-3).

2. **Toast notifications:** Available via JS `app.extensionManager.toast.add()` with severity levels (success, info, warn, error). Useful for non-fatal warnings (e.g., "Parameter X not supported by backend, ignored").

3. **VALIDATE_INPUTS:** Runs before execution. Returns `True` or an error string. Validation failure prevents execution and shows the error. Good for catching obviously invalid configurations before HTTP calls.

4. **Logging:** Standard Python `logging` module. Output appears in ComfyUI's console/terminal.

**Confidence: Confirmed** -- documented in official docs and JS extension API.

Sources:
- [ComfyUI Backend Properties](https://docs.comfy.org/custom-nodes/backend/server_overview)
- [ComfyUI Toast API](https://docs.comfy.org/custom-nodes/js/javascript_toast)

### P-5: Config Reload/Caching

**Status: Assumed, recommendation based on patterns**

No official ComfyUI guidance on config file caching for node packs. Ecosystem convention: load config at import time (module load), cache in a module-level variable. Provide a mechanism to reload (either a PromptServer endpoint triggered by frontend, or reload on each execution).

**Recommendation:** Cache on module load. Provide a `/llm-bikeshed/reload-config` PromptServer endpoint. The frontend can offer a "Reload Config" button. Config changes during a session are rare (API key updates, URL changes). Per-execution reload is unnecessary overhead.

**Confidence: Assumed** -- no authoritative source, but reasonable engineering decision.

---

## 2. Per-Backend API Research (API-4)

### Ollama Native API

**Endpoint:** `POST {url}/api/chat`

**Parameters (in `options` field):**

| Parameter | Type | Default | Category |
|-----------|------|---------|----------|
| temperature | float | 0.8 | Sampling |
| top_k | int | 40 | Sampling |
| top_p | float | 0.9 | Sampling |
| min_p | float | 0.0 | Sampling |
| seed | int | 0 | Sampling |
| num_predict | int | -1 (unlimited) | Generation |
| num_ctx | int | 2048 | Generation |
| stop | string/list | -- | Generation |
| repeat_penalty | float | 1.0 | Repetition |
| repeat_last_n | int | 64 | Repetition |
| presence_penalty | float | 0.0 | Repetition |
| frequency_penalty | float | 0.0 | Repetition |
| mirostat | int | 0 | Mirostat (0=off, 1=v1, 2=v2) |
| mirostat_eta | float | 0.1 | Mirostat |
| mirostat_tau | float | 5.0 | Mirostat |
| tfs_z | float | 1.0 | Tail-free sampling |
| typical_p | float | 1.0 | Typical sampling |
| penalize_newline | bool | -- | Repetition |
| num_keep | int | -- | Context |
| num_batch | int | -- | Performance |
| num_gpu | int | -- | Hardware |
| num_thread | int | -- | Hardware |

**Top-level request parameters (not in `options`):**
- `model` (string, required)
- `messages` (array, required)
- `stream` (bool, default true)
- `format` (string/object -- "json" or JSON schema)
- `keep_alive` (string/number -- e.g., "5m", "30s", 0 to unload immediately)
- `tools` (array)
- `think` (bool/string)

**Unknown parameter handling:** The `options` field is typed as `map[string]interface{}` with `additionalProperties: true`. Unknown keys are accepted but silently ignored by the model runner. **Confirmed safe to send extra params.**

**Confidence: Confirmed** -- from official Ollama API docs and modelfile reference.

Sources:
- [Ollama /api/chat](https://docs.ollama.com/api/chat)
- [Ollama Modelfile Reference](https://docs.ollama.com/modelfile)

### LM Studio (OpenAI-Compatible)

**Endpoint:** `POST {url}/v1/chat/completions`

**Standard OAI parameters:** model, messages, temperature, top_p, max_tokens, stream, stop, presence_penalty, frequency_penalty, logit_bias, seed

**LM Studio extensions beyond OAI:**

| Parameter | Type | Default | Notes |
|-----------|------|---------|-------|
| top_k | int | -- | Token selection filter |
| repeat_penalty | float | -- | Repetition penalty |
| ttl | int (seconds) | 3600 (60 min app default) | Model idle timeout, per-request |
| draft_model | string | -- | Speculative decoding |

**Model management:**
- JIT (Just-In-Time) loading: models load automatically on first request
- TTL resets on each request (timer-based, same as Ollama's keep_alive)
- Auto-Evict: when enabled (default), loading a new JIT model unloads the previous one
- Default TTL is 60 minutes (configurable in Developer Settings)

**Model list endpoint:** `GET {url}/v1/models`

**Unknown parameter handling:** Not explicitly documented. LM Studio uses llama.cpp under the hood and likely ignores unknown top-level request parameters. Parameters like `top_k` and `repeat_penalty` are sent via `extra_body` in the OpenAI Python SDK, but via raw HTTP they go in the request body directly. **Likely safe but needs testing.**

**Confidence: Confirmed** for documented params, **Likely** for unknown param handling.

Sources:
- [LM Studio Chat Completions](https://lmstudio.ai/docs/developer/openai-compat/chat-completions)
- [LM Studio TTL and Auto-Evict](https://lmstudio.ai/docs/developer/core/ttl-and-auto-evict)

### text-generation-webui (OpenAI-Compatible)

**Endpoint:** `POST {url}/v1/chat/completions`

**Standard OAI parameters:** model, messages, temperature, top_p, max_tokens, stream, stop, presence_penalty, frequency_penalty, logit_bias, n

**text-gen-webui extensions (GenerationOptions class):**

| Parameter | Type | Default | Notes |
|-----------|------|---------|-------|
| top_k | int | -- | Sampling |
| typical_p | float | 1.0 | Typical sampling |
| min_p | float | -- | Minimum probability |
| repeat_penalty | float | -- | Repetition penalty |
| seed | int | -- | Reproducibility |
| preset | string | -- | Server-side preset name |
| sampler_priority | list[str] | -- | Custom sampler order |
| mode | string | "instruct" | instruct/chat/chat-instruct |
| instruction_template | string | -- | Template name |
| continue_ | bool | False | Continue previous generation |
| dynamic_temperature | bool | -- | Dynamic temp scaling |
| tfs | float | -- | Tail-free sampling |
| top_a | float | -- | Top-A sampling |

**Model management endpoints (require admin key):**
- `GET {url}/v1/internal/model/list` -- list available models
- `POST {url}/v1/internal/model/load` -- load model (body: `{"model_name": "...", "args": {...}}`)
- `POST {url}/v1/internal/model/unload` -- unload current model
- `GET {url}/v1/internal/model/info` -- current model info

**Admin key handling (API-7):**
- `--api-key KEY` -- protects all endpoints
- `--admin-key ADMIN_KEY` -- separate key for admin operations (load/unload/list)
- If `--admin-key` not set, `--api-key` is used for admin operations too
- **Confirmed: admin key can be separate from API key.** Config should support both: `api_key` for generation, `admin_key` for model management. If only one is configured, use it for both.

**Unknown parameter handling:** Not explicitly documented. The Pydantic model likely rejects unknown top-level fields. However, the `GenerationOptions` class is extensive enough that most useful parameters are included. **Needs testing.**

**Confidence: Confirmed** for endpoints and auth, **Assumed** for unknown param handling.

Sources:
- [text-gen-webui OpenAI API wiki](https://github.com/oobabooga/text-generation-webui/wiki/12-%E2%80%90-OpenAI-API)
- [text-gen-webui typing.py](https://github.com/oobabooga/text-generation-webui/blob/main/extensions/openai/typing.py)

### Cross-Backend Parameter Mapping

| Concept | Ollama Native | LM Studio (OAI) | text-gen-webui (OAI) |
|---------|--------------|-----------------|---------------------|
| Temperature | `options.temperature` | `temperature` | `temperature` |
| Max tokens | `options.num_predict` | `max_tokens` | `max_tokens` |
| Top-P | `options.top_p` | `top_p` | `top_p` |
| Top-K | `options.top_k` | `top_k` | `top_k` |
| Min-P | `options.min_p` | -- | `min_p` |
| Seed | `options.seed` | `seed` | `seed` |
| Stop sequences | `options.stop` | `stop` | `stop` |
| Repeat penalty | `options.repeat_penalty` | `repeat_penalty` | `repeat_penalty` |
| Presence penalty | `options.presence_penalty` | `presence_penalty` | `presence_penalty` |
| Frequency penalty | `options.frequency_penalty` | `frequency_penalty` | `frequency_penalty` |
| Context size | `options.num_ctx` | -- (server config) | -- (server config) |
| Mirostat | `options.mirostat` | -- | -- |
| Mirostat eta | `options.mirostat_eta` | -- | -- |
| Mirostat tau | `options.mirostat_tau` | -- | -- |
| TFS | `options.tfs_z` | -- | `tfs` |
| Typical P | `options.typical_p` | -- | `typical_p` |
| Model keep-alive | `keep_alive` (top-level) | `ttl` (top-level) | explicit unload endpoint |

**Key findings for Options node design (A-1, A-2, A-3):**

Cross-provider parameters (candidates for shared Options node):
- `temperature`, `max_tokens`/`num_predict`, `top_p`, `top_k`, `seed`, `stop`, `repeat_penalty`, `presence_penalty`, `frequency_penalty`

Ollama-only parameters:
- `mirostat`, `mirostat_eta`, `mirostat_tau`, `num_ctx`, `repeat_last_n`, `tfs_z`, `typical_p`, `penalize_newline`, `num_keep`, `min_p`

LM Studio-only extensions: None beyond the cross-provider set (it's a clean OAI-compat implementation).

text-gen-webui unique: `typical_p`, `tfs`, `min_p`, `dynamic_temperature`, `top_a`, `sampler_priority`, `preset`

**Recommendation for A-1:** Per-provider Options nodes. The cross-provider parameter overlap is significant, but the parameter *names* differ (e.g., `num_predict` vs `max_tokens`, `tfs_z` vs `tfs`), and the adapter layer already handles name mapping. A shared base + provider-specific approach adds complexity without much user benefit since provider is already fixed by the Provider node choice. Each Options node shows only parameters its backend actually supports.

---

## 3. Ecosystem Analysis

### comfyui-ollama (stavsap)

**Architecture patterns worth borrowing:**

1. **Custom type flow:** `OLLAMA_CONNECTIVITY` -> `OLLAMA_OPTIONS` -> `OLLAMA_META` pipeline. Clean separation. Our equivalent: `LLM_PROVIDER` -> `LLM_OPTIONS` -> `LLM_META`.

2. **Toggle-based Options:** OllamaOptionsV2 uses a BOOLEAN per parameter (e.g., `enable_temperature`). Only enabled params are included in API calls. `get_request_options()` method iterates toggles. This is exactly the pattern we're considering (A-3).

3. **Meta passthrough:** GenerateV2 accepts either direct connectivity/options or inherits via meta. Explicit inputs override meta values. This is our designed pattern.

4. **Dynamic model dropdown:** Custom PromptServer endpoint (`POST /ollama/get_models`) queries the Ollama server via SDK. Frontend JS calls this and populates COMBO widget.

5. **Uses `ollama` Python SDK:** Our project avoids SDKs and uses `requests` directly. This is a deliberate difference -- no SDK dependency conflicts.

**Anti-patterns to avoid:**
- The SDK dependency means comfyui-ollama breaks when the `ollama` package updates with breaking changes
- V1 nodes (monolithic) are still present alongside V2 nodes, creating user confusion
- Very tall OllamaOptionsV2 node due to toggle+value pair per parameter

### comfyui-ollama-describer (alisson-anjos)

**Compact approach:** Self-contained nodes with inline parameters (temperature, top_k, top_p, repeat_penalty, seed, num_ctx). Model selection via hardcoded model name field (not dynamic dropdown). Uses `requests` directly (no SDK).

**Structured output:** Accepts JSON schema as input, passes to Ollama's `format` parameter.

**Pattern to borrow:** Simplicity of inline parameters for the Basic generation node.

**Anti-patterns:** Hardcoded model list that may trigger unwanted downloads. No provider abstraction.

---

## 4. Implementation Feasibility

### Synchronous HTTP in FUNCTION Methods

**Status: Confirmed standard pattern**

ComfyUI node FUNCTION methods run synchronously. Using `requests` (sync HTTP) is the standard approach. comfyui-ollama uses the synchronous `ollama` SDK in FUNCTION methods. Our project uses `requests` directly (I-1 confirmed).

```python
import requests

def generate(self, provider, prompt, system_prompt="", **kwargs):
    response = requests.post(
        f"{provider['url']}/api/chat",
        json=payload,
        timeout=provider.get('timeout', 120)
    )
    response.raise_for_status()
    return (response.json()["message"]["content"],)
```

### asyncio.to_thread for PromptServer Endpoints

**Status: Confirmed pattern**

PromptServer uses aiohttp and runs async. Custom endpoints registered via `@PromptServer.instance.routes.post("/path")` are async. To call synchronous `requests` from these endpoints:

```python
from aiohttp import web
from server import PromptServer
import asyncio
import requests

@PromptServer.instance.routes.post("/llm-bikeshed/models")
async def get_models(request):
    data = await request.json()
    url = data.get("url", "http://localhost:11434")
    # Run sync HTTP in thread pool
    response = await asyncio.to_thread(
        requests.get, f"{url}/api/tags", timeout=10
    )
    models = response.json().get("models", [])
    return web.json_response({"models": [m["name"] for m in models]})
```

### Custom Type Registration

**Status: Confirmed trivial**

Custom types are just uppercase strings. No registration needed beyond using them consistently in `RETURN_TYPES` and `INPUT_TYPES`:

```python
# Provider node
RETURN_TYPES = ("LLM_PROVIDER",)

# Generation node
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
        }
    }
```

Custom types display as connection-only inputs (no widget). `forceInput` is not needed for custom types -- they cannot render as widgets.

### Frontend JS for Dynamic Model Dropdowns

**Status: Confirmed pattern from ecosystem**

Pattern from comfyui-ollama and other packs:

1. **Backend:** Register PromptServer endpoint that queries backend for model list
2. **Frontend:** In `nodeCreated` hook, add a custom widget or modify the COMBO widget
3. **Refresh:** Add a button widget that re-fetches models on click

The recommended approach for our project:

```javascript
// js/model_dropdown.js
import { app } from "../../scripts/app.js";

app.registerExtension({
    name: "llm-bikeshed.model-dropdown",
    async nodeCreated(node) {
        if (["LLMProviderOllama", "LLMProviderLMStudio", "LLMProviderTextGenWebUI"].includes(node.comfyClass)) {
            // Find the model widget and add refresh logic
            const modelWidget = node.widgets.find(w => w.name === "model");
            // Fetch models from backend endpoint
            // Update widget options
        }
    }
});
```

**Confidence: Confirmed** -- established ecosystem pattern.

---

## 5. Registry and Publishing

### pyproject.toml Requirements

```toml
[project]
name = "comfyui-llm-bikeshed"
version = "0.1.0"
description = "Local LLM text generation nodes for ComfyUI"
license = {file = "LICENSE"}
requires-python = ">=3.10"
dependencies = ["pyyaml>=6.0", "requests>=2.28.0"]

[project.urls]
Repository = "https://github.com/user/comfyui-llm-bikeshed"

[tool.comfy]
PublisherId = "TBD"
DisplayName = "LLM Bikeshed"
```

Note: `pillow` and `numpy` are ComfyUI dependencies, not ours. We don't need torch either. The dependency list is minimal: `pyyaml` + `requests`.

**Dependency change from CLAUDE.md:** The original design specified `aiohttp` for HTTP. The resolution tracker (I-1) confirmed switching to `requests` (sync). This means we need `requests` in dependencies, not `aiohttp`. `aiohttp` is already available via ComfyUI's PromptServer but we don't import it for node HTTP calls.

### Security Prohibitions

| Prohibited | Reason |
|------------|--------|
| `eval()` / `exec()` | RCE risk, registry will reject |
| `subprocess pip install` | Supply chain attack vector |
| Code obfuscation | Cannot be reviewed |

Our project has no need for any of these. YAML parsing via `pyyaml` is safe with `yaml.safe_load()`.

**Confidence: Confirmed** -- from official registry docs.

Source: [ComfyUI Registry Standards](https://docs.comfy.org/registry/standards)

---

## 6. Related Specs

No other specs exist in this project. This is the only spec.

---

## 7. Quality Commands

No package.json, Makefile, or CI configs exist yet (pre-implementation project). Quality commands will be established during scaffold phase.

| Type | Command | Source |
|------|---------|--------|
| Lint | Not found | -- |
| TypeCheck | Not found | -- |
| Unit Test | Not found | -- |
| Build | Not found | -- |

---

## 8. Verification Tooling

**Project Type:** ComfyUI custom node pack (Python backend + JS frontend)

No automated E2E tooling detected. This is a ComfyUI extension, not a standalone app.

**Verification Strategy:**
1. Install into ComfyUI custom_nodes directory
2. Verify nodes appear in ComfyUI menu
3. Test with running Ollama/LM Studio/text-gen-webui instances
4. Manual workflow testing

---

## Feasibility Assessment

| Aspect | Assessment | Notes |
|--------|------------|-------|
| Technical Viability | **High** | All platform capabilities confirmed. Ecosystem patterns established. |
| Effort Estimate | **L** | 3 provider nodes, 2 gen nodes, options nodes, 2 adapters, config system, frontend JS, presets |
| Risk Level | **Low** | No novel platform challenges. Main risk is scope creep. |

---

## Recommendations for Requirements

1. **P-10 resolved: Use PROMPT reverse-indexing for unload deferral (A-15).** The generation node's FUNCTION method checks if its meta output connects to another generation node. If yes, skip unload. If no (or no meta output connection), fire unload. This is clean and requires no timers or manual toggles.

2. **Options node architecture (A-1): Per-provider Options nodes with toggles (A-3).** Each provider gets its own Options node showing only its supported parameters. Each parameter has a BOOLEAN enable toggle. Disabled = model default. This avoids the complexity of shared base + provider-specific chaining while giving explicit control.

3. **Model selection (P-2/P-3): Custom widget via JS, not backend COMBO.** Frontend JS fetches model lists from PromptServer endpoints. Saved model names persist in widgets_values regardless of backend state. Include a refresh button.

4. **Preset mechanism (A-6): Separate Preset Loader node for v1.** Known-working pattern, no JS complexity. Inline COMBO approach is a future UX enhancement.

5. **Dependency change: Use `requests` instead of `aiohttp`.** Confirmed by I-1. Simpler, synchronous, matches ecosystem patterns. `aiohttp` is available from ComfyUI for PromptServer endpoints but not needed for node HTTP calls.

6. **Admin key separation (API-7): Config supports both `api_key` and `admin_key` for text-gen-webui.** If only `api_key` is set, use it for admin operations too (matches text-gen-webui's fallback behavior).

7. **Error handling (I-3): Raise exceptions to halt workflow.** Use VALIDATE_INPUTS for pre-execution checks (URL format, required config). Use toast notifications for non-fatal warnings (unsupported param ignored).

8. **Config caching (P-5): Load at module import, provide reload endpoint.** Per-execution reload is unnecessary.

---

## Open Questions

1. **Unknown parameter handling for LM Studio and text-gen-webui:** Ollama confirmed safe (additionalProperties: true). LM Studio and text-gen-webui need empirical testing. Recommendation: implement adapter allowlists regardless (only send known params), but don't error on the adapter side if a param is in the allowlist but the backend rejects it.

2. **text-gen-webui model list without admin key:** Can `GET /v1/internal/model/list` work without `--admin-key`? If the user hasn't configured admin auth, can we still list models? Needs testing.

3. **IS_CHANGED on Provider nodes (A-11):** Using `float("NaN")` forces re-execution every time, which means the model list endpoint gets hit on every execution. Consider using a hash of the provider config instead, or just not implementing IS_CHANGED (let ComfyUI's default caching work).

---

## Sources

- [ComfyUI Hidden Inputs](https://docs.comfy.org/custom-nodes/backend/more_on_inputs)
- [ComfyUI Data Types](https://docs.comfy.org/custom-nodes/backend/datatypes)
- [ComfyUI Backend Properties](https://docs.comfy.org/custom-nodes/backend/server_overview)
- [ComfyUI JS Extensions](https://docs.comfy.org/custom-nodes/js/javascript_overview)
- [ComfyUI Toast API](https://docs.comfy.org/custom-nodes/js/javascript_toast)
- [ComfyUI Registry Standards](https://docs.comfy.org/registry/standards)
- [ComfyUI Workflow JSON Format (DeepWiki)](https://deepwiki.com/Comfy-Org/ComfyUI/7.3-workflow-json-format)
- [Ollama /api/chat](https://docs.ollama.com/api/chat)
- [Ollama Modelfile Reference](https://docs.ollama.com/modelfile)
- [LM Studio Chat Completions](https://lmstudio.ai/docs/developer/openai-compat/chat-completions)
- [LM Studio TTL and Auto-Evict](https://lmstudio.ai/docs/developer/core/ttl-and-auto-evict)
- [text-gen-webui OpenAI API](https://github.com/oobabooga/text-generation-webui/wiki/12-%E2%80%90-OpenAI-API)
- [text-gen-webui typing.py](https://github.com/oobabooga/text-generation-webui/blob/main/extensions/openai/typing.py)
- [ComfyUI-Ollama (DeepWiki)](https://deepwiki.com/stavsap/comfyui-ollama/1-overview)
- [ComfyUI-Ollama source](https://github.com/stavsap/comfyui-ollama)
- [ComfyUI-Ollama-Describer source](https://github.com/alisson-anjos/ComfyUI-Ollama-Describer)
