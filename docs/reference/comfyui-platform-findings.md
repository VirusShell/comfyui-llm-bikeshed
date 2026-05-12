# ComfyUI Platform Findings

> **Last updated:** 2026-03-09
> **Applies to:** ComfyUI V1 node spec
> **Resolution tracker items:** P-2, P-3, P-4, P-5, P-9, P-10

---

## P-10: Graph Topology Introspection (RESOLVED)

**Can a node's FUNCTION method determine what its outputs connect to?**

**Yes**, via reverse-indexing the PROMPT hidden input.

### How It Works

The `PROMPT` hidden input provides the full execution graph as a dict keyed by node ID. Each node entry contains `class_type` and `inputs`. Input connections use the format `[source_node_id, output_index]`.

PROMPT does NOT directly tell a node what its outputs connect to. But a node CAN reverse-index the graph to find downstream connections:

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

### Usage for Unload Deferral (A-15)

Declare hidden inputs:
```python
"hidden": {"prompt": "PROMPT", "unique_id": "UNIQUE_ID"}
```

In FUNCTION method, check if meta output connects to another generation node. If yes, skip unload. If no, fire unload.

**Caveat:** `DYNPROMPT` may differ from `PROMPT` if Node Expansion is used, but our nodes do not use expansion.

**Confidence:** Confirmed

---

## P-9: Boolean Toggle Widget Save/Load (RESOLVED)

BOOLEAN is a first-class primitive type. Standard serialization to `widgets_values`. No known save/load issues.

```python
"enable_temperature": ("BOOLEAN", {"default": False, "label_on": "ON", "label_off": "OFF"})
```

**Confidence:** Confirmed

---

## P-2/P-3: Dynamic COMBO and Offline Fallback (RESOLVED)

### Recommended Approach: Frontend JS + PromptServer Endpoint

Don't use backend `INPUT_TYPES` for model lists. Use frontend JS:

1. **Backend:** Register PromptServer endpoint that queries backend for model list
2. **Frontend:** In `nodeCreated` hook, populate COMBO widget from endpoint response
3. **Refresh:** Add button widget to re-fetch models on click
4. **Offline:** Show fallback entry ("Backend offline" or last-known list)
5. **Saved workflows:** Model name persists in `widgets_values` regardless of current backend state

This is how comfyui-ollama does it (POST `/ollama/get_models`).

### Fallback for Offline

Instead of COMBO-to-text dynamic switching (complex, fragile), use a STRING input with `defaultInput: True`. User can type a model name manually or connect from another node. The COMBO dropdown is a convenience, not the authoritative input.

**Confidence:** Likely (follows established ecosystem patterns)

---

## P-4: Error Display Mechanisms (RESOLVED)

| Mechanism | When to Use | Behavior |
|-----------|------------|----------|
| Exception in FUNCTION | Fatal errors (API failure, invalid config) | Halts workflow, red outline on node, error notification |
| `VALIDATE_INPUTS` | Pre-execution checks (URL format, required fields) | Prevents execution, shows error string |
| Toast notifications (JS) | Non-fatal warnings (param ignored, config reload) | `app.extensionManager.toast.add()` with severity |
| Python `logging` | Debug/info output | Appears in ComfyUI console |

**Decided approach (I-3):** Raise exceptions for errors. Use VALIDATE_INPUTS for obvious misconfigurations. Toast for informational warnings.

**Confidence:** Confirmed

---

## P-5: Config Reload/Caching (DECIDED)

No official ComfyUI guidance. Ecosystem convention: load at import time, cache in module-level variable.

**Decision:** Cache on module load. Provide `/llm-bikeshed/reload-config` PromptServer endpoint. Frontend can offer "Reload Config" button. Per-execution reload is unnecessary overhead.

**Confidence:** Assumed (reasonable engineering decision, no authoritative source)

---

## Custom Types

Custom types (LLM_PROVIDER, LLM_OPTIONS, LLM_META) are just uppercase strings. No registration API needed. They display as connection-only inputs (no widget). `forceInput` not needed — custom types cannot render as widgets.

```python
RETURN_TYPES = ("LLM_PROVIDER",)

# In another node:
"provider": ("LLM_PROVIDER",),  # connection-only, no widget
```

**Confidence:** Confirmed

---

## Synchronous HTTP in Node FUNCTION Methods

ComfyUI node FUNCTION methods run synchronously. `requests` (sync HTTP) is the standard approach for API calls within nodes. Confirmed by ecosystem analysis (comfyui-ollama uses synchronous SDK calls).

For PromptServer endpoints (async context), use `asyncio.to_thread()`:

```python
@PromptServer.instance.routes.post("/llm-bikeshed/models")
async def get_models(request):
    data = await request.json()
    response = await asyncio.to_thread(
        requests.get, f"{data['url']}/api/tags", timeout=10
    )
    return web.json_response(response.json())
```

**Confidence:** Confirmed

---

## IS_CHANGED Considerations (A-11)

Using `float("NaN")` forces re-execution every time. For generation nodes this is correct (LLM calls are non-deterministic).

For Provider nodes, `float("NaN")` would trigger unnecessary model list API calls on every execution. **Recommendation:** Don't implement IS_CHANGED on Provider nodes — let ComfyUI's default caching work. The Provider output only changes when its widget values change.

---

## Textgen verified behavior (see also)

Upstream `oobabooga/textgen` auth and internal model HTTP behavior (not ComfyUI-specific): [`docs/research/textgen-lifecycle-verified.md`](../research/textgen-lifecycle-verified.md).

## Sources

- [ComfyUI Hidden Inputs](https://docs.comfy.org/custom-nodes/backend/more_on_inputs)
- [ComfyUI Data Types](https://docs.comfy.org/custom-nodes/backend/datatypes)
- [ComfyUI Backend Properties](https://docs.comfy.org/custom-nodes/backend/server_overview)
- [ComfyUI JS Extensions](https://docs.comfy.org/custom-nodes/js/javascript_overview)
- [ComfyUI Toast API](https://docs.comfy.org/custom-nodes/js/javascript_toast)
