# ComfyUI Custom Node Development Reference

> **Last updated:** 2026-02-22
> **Verified against:** ComfyUI frontend v1.38.13, Comfy-Org/ComfyUI master branch
> **Scope:** General ComfyUI node development knowledge, not project-specific

---

## Table of Contents

1. [Node Execution Lifecycle](#1-node-execution-lifecycle)
2. [Input System](#2-input-system)
3. [Output System](#3-output-system)
4. [Error Handling & User Feedback](#4-error-handling--user-feedback)
5. [Image/Tensor Handling](#5-imagetensor-handling)
6. [Frontend JavaScript](#6-frontend-javascript)
7. [Custom API Endpoints](#7-custom-api-endpoints)
8. [Configuration & Secrets](#8-configuration--secrets)
9. [Publishing & Distribution](#9-publishing--distribution)
10. [V3 Node Specification](#10-v3-node-specification)
11. [Ecosystem Patterns](#11-ecosystem-patterns)
12. [Flags & Open Questions](#12-flags--open-questions)

---

## 1. Node Execution Lifecycle

### 1.1 Discovery and Loading

When ComfyUI starts, it scans the `custom_nodes` directory for Python modules and attempts to load them. A module is recognized as a custom node pack if it exports `NODE_CLASS_MAPPINGS` from its `__init__.py`.

If the `__init__.py` raises an exception during import, ComfyUI continues startup but reports the module as having failed to load. This is logged to the console.

**Source:** [Lifecycle - ComfyUI Docs](https://docs.comfy.org/custom-nodes/backend/lifecycle), accessed 2026-02-22

#### Registration Pattern (`__init__.py`)

```python
from .nodes import NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS

WEB_DIRECTORY = "./web"  # or "./js" -- both valid conventions
__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS', 'WEB_DIRECTORY']
```

- `NODE_CLASS_MAPPINGS`: `dict[str, type]` -- Maps internal node names to Python classes. The key is the unique identifier used in workflow JSON. Must not collide with other node packs.
- `NODE_DISPLAY_NAME_MAPPINGS`: `dict[str, str]` -- Maps internal names to human-readable display names shown in the UI menu.
- `WEB_DIRECTORY`: `str` -- Path to directory containing frontend JavaScript files. Files are auto-served by ComfyUI. Both `"./web"` and `"./js"` are valid.

**Source:** [Getting Started - ComfyUI Docs](https://docs.comfy.org/custom-nodes/walkthrough), accessed 2026-02-22

### 1.2 Execution Model

ComfyUI uses a **front-to-back topological sort** execution model (changed from back-to-front recursive in PR #2666). The execution engine:

1. Receives a prompt (workflow graph) via the `/prompt` endpoint
2. Validates the prompt (type checking, `VALIDATE_INPUTS`)
3. Topologically sorts the nodes
4. Executes nodes front-to-back, respecting data dependencies
5. Caches outputs for reuse

**Execution order is non-deterministic** beyond graph structure constraints. The docs explicitly state: "Execution order has always changed depending on which nodes happen to have which IDs, but it may now change depending on which values are cached as well." Do not build assumptions around execution sequencing.

**Source:** [Execution Model Inversion Guide](https://docs.comfy.org/development/comfyui-server/execution_model_inversion_guide), accessed 2026-02-22

### 1.3 Threading Model

ComfyUI's server runs on an asyncio event loop (aiohttp). Node FUNCTION methods are called from within this event loop context via `_async_map_node_over_list()`.

**Critical implication for async code:** You **cannot** call `asyncio.run()` inside a node's FUNCTION method because an event loop is already running. This throws `RuntimeError: asyncio.run() cannot be called from a running event loop`.

Workarounds:
- **Make the FUNCTION async** and use `await` directly (recent ComfyUI versions support this, but this is not officially documented and should be tested)
- **Use `asyncio.get_event_loop().run_until_complete()`** -- may work in some contexts but is fragile
- **Use synchronous HTTP** (e.g., `requests` or `aiohttp` with a dedicated thread) as a simpler alternative

Multiple custom node packs have hit this issue. See [Comfy-Org/ComfyUI#9007](https://github.com/Comfy-Org/ComfyUI/issues/9007).

> **FLAG - Documentation Gap:** The official docs do not specify whether node FUNCTION methods can be async. Community evidence suggests recent ComfyUI versions execute them in an async context, but this is undocumented. This is a critical detail for any node pack using async HTTP clients like aiohttp.

**Source:** [ComfyUI#9007](https://github.com/Comfy-Org/ComfyUI/issues/9007), [ComfyUI#9962](https://github.com/comfyanonymous/ComfyUI/issues/9962), accessed 2026-02-22

### 1.4 Caching and IS_CHANGED

ComfyUI caches node outputs to avoid redundant computation. The caching system uses **input signature-based keys**: if a node's inputs have not changed since the last run, its cached outputs are reused.

Four cache strategies exist:
- **Classic** (default): Unbounded growth, best performance, no eviction
- **LRU**: Bounded size, least-recently-used eviction
- **RAM_PRESSURE**: Dynamic eviction based on available memory
- **NONE**: No caching at all

#### IS_CHANGED Classmethod

`IS_CHANGED` is a classmethod that receives the same arguments as FUNCTION. Its return value is compared with the previous run's return value. If `is_changed != is_changed_old`, the node re-executes.

```python
@classmethod
def IS_CHANGED(cls, **kwargs):
    # Return float("NaN") to ALWAYS re-execute (NaN != NaN is True)
    return float("NaN")

    # Or return a hash for efficient change detection:
    # return hashlib.md5(open(image_path, 'rb').read()).hexdigest()
```

- The return value is **not** a boolean. It is any Python object that supports equality comparison.
- `float("NaN")` forces re-execution because `NaN != NaN` is always `True`.
- If `IS_CHANGED` itself raises an exception, the node's is_changed value is set to `float("NaN")`, forcing re-execution as a safety measure.
- The built-in `LoadImage` node returns a hash of the image file -- it only re-executes when the file actually changes.

> **FLAG - Common Mistake:** Developers frequently misunderstand `IS_CHANGED` as returning a boolean. `return True` does NOT mean "always re-execute" -- it means "the fingerprint is the boolean value True." If you returned True last time too, the node will NOT re-execute because `True == True`. Use `float("NaN")` for forced re-execution, or return a value that actually changes when re-execution is needed.

**Source:** [Properties - ComfyUI Docs](https://docs.comfy.org/custom-nodes/backend/server_overview), [ComfyUI#4962](https://github.com/comfyanonymous/ComfyUI/issues/4962), accessed 2026-02-22

### 1.5 Exception Handling During Execution

When a node's FUNCTION method raises an exception:

1. **The entire workflow halts.** There is no per-branch or per-node error isolation. The remaining nodes in the execution queue do not run.
2. **An `execution_error` WebSocket message** is sent to connected clients containing `node_id`, `node_type`, `exception_type`, and `exception_message`.
3. **The UI highlights the failed node** (red outline) and displays the error message.
4. **The traceback is logged** to the server console.
5. **There is no cleanup or rollback mechanism.** Nodes that already executed retain their outputs in cache.

There is no built-in try/catch or error recovery mechanism at the workflow level. Custom nodes that want graceful error handling must catch exceptions internally and return error values through their normal output types.

**Source:** [ComfyUI Discussion #3643](https://github.com/comfyanonymous/ComfyUI/discussions/3643), [ComfyUI#11048](https://github.com/Comfy-Org/ComfyUI/issues/11048), accessed 2026-02-22

### 1.6 OUTPUT_NODE Behavior

Setting `OUTPUT_NODE = True` marks a node as an output/terminal node. This has two effects:

1. **The node always executes** when it is part of the active graph, even if nothing downstream depends on it. Without `OUTPUT_NODE = True`, a node only executes if its outputs are consumed by another node.
2. **It enables the "play" button** in the UI context for that node.

Typical output nodes: image savers, preview nodes, display nodes. Any node whose purpose is a side effect (saving, displaying, sending data) rather than producing data for other nodes should set `OUTPUT_NODE = True`.

**Source:** [Properties - ComfyUI Docs](https://docs.comfy.org/custom-nodes/backend/server_overview), accessed 2026-02-22

---

## 2. Input System

### 2.1 INPUT_TYPES Structure

`INPUT_TYPES` is a `@classmethod` that returns a dictionary with up to three keys:

```python
@classmethod
def INPUT_TYPES(cls):
    return {
        "required": {
            "name": ("TYPE", {options}),
        },
        "optional": {
            "name": ("TYPE", {options}),
        },
        "hidden": {
            "name": "HIDDEN_TYPE",
        },
    }
```

Because it is a classmethod, it can compute values dynamically at registration time (e.g., scanning a directory for files to populate a COMBO dropdown).

### 2.2 Input Categories

| Category | Behavior |
|----------|----------|
| **required** | Must be provided. Appears as a mandatory widget or connection slot. Workflow fails validation if not connected or filled. |
| **optional** | Can be left empty. Function receives the value only when connected/filled. Provide Python default values in the function signature. |
| **hidden** | Server-provided values, no UI widget. Values are injected by ComfyUI at execution time. |

#### Hidden Input Types

| Type | Value Provided |
|------|---------------|
| `"UNIQUE_ID"` | The unique identifier of the node instance, matching `node.id` on the client side |
| `"PROMPT"` | The complete prompt dict sent by the client to the server |
| `"EXTRA_PNGINFO"` | A dict that gets copied into metadata of any `.png` files saved during execution |
| `"DYNPROMPT"` | An instance for advanced use cases (node expansion, loops). Unlike PROMPT, this may mutate during execution |

**Source:** [Hidden and Flexible Inputs - ComfyUI Docs](https://docs.comfy.org/custom-nodes/backend/more_on_inputs), accessed 2026-02-22

### 2.3 Widget Types and Configuration

#### STRING

```python
"prompt": ("STRING", {
    "default": "",
    "multiline": True,         # Renders as textarea vs single-line input
    "placeholder": "Enter text...",
    "dynamicPrompts": True,    # Enable dynamic prompt syntax (wildcards, etc.)
    "tooltip": "Description shown on hover",
})
```

Returns: Python `str`

#### INT

```python
"count": ("INT", {
    "default": 1,
    "min": 0,
    "max": 100,
    "step": 1,                 # Increment amount for slider/spinner
    "display": "number",       # "number" (spinner) or "slider"
    "tooltip": "Number of items",
})
```

Returns: Python `int`

#### FLOAT

```python
"temperature": ("FLOAT", {
    "default": 0.7,
    "min": 0.0,
    "max": 2.0,
    "step": 0.01,
    "display": "number",       # "number" or "slider"
    "tooltip": "Sampling temperature",
})
```

Returns: Python `float`

#### BOOLEAN

```python
"enabled": ("BOOLEAN", {
    "default": True,
    "label_on": "Enabled",
    "label_off": "Disabled",
    "tooltip": "Toggle this feature",
})
```

Returns: Python `bool`

#### COMBO (Dropdown)

```python
"mode": (["option_a", "option_b", "option_c"],)
# Note: no TYPE string -- the list itself IS the type specification
```

Returns: Python `str` (the selected option)

COMBO values can be computed dynamically in INPUT_TYPES since it is a classmethod:

```python
@classmethod
def INPUT_TYPES(cls):
    files = os.listdir(some_directory)
    return {
        "required": {
            "file": (files,),
        }
    }
```

**Source:** [Datatypes - ComfyUI Docs](https://docs.comfy.org/custom-nodes/backend/datatypes), [Properties - ComfyUI Docs](https://docs.comfy.org/custom-nodes/backend/server_overview), accessed 2026-02-22

### 2.4 Common Input Options (All Types)

| Option | Type | Purpose |
|--------|------|---------|
| `default` | varies | Initial value. Required for INT and FLOAT per docs. |
| `forceInput` | `bool` | Prevents widget creation entirely. The input appears ONLY as a connection slot. Cannot be converted back to widget. |
| `defaultInput` | `bool` | Widget defaults to showing as an input connection slot, but user can convert it back to a widget via right-click menu. |
| `tooltip` | `str` | Descriptive text shown on hover in the UI. |
| `lazy` | `bool` | Marks the input for lazy evaluation (see Section 2.7). |
| `rawLink` | `bool` | Receive `["nodeId", outputIndex]` instead of the evaluated value. Advanced use case. |

#### forceInput vs defaultInput

- `forceInput: True` -- The input is **always** a connection slot. No widget is ever created. The user cannot convert it to a widget. Use this for custom datatypes that have no meaningful widget representation (e.g., `"LLM_PROVIDER"`).
- `defaultInput: True` -- The input **starts** as a connection slot, but the user can right-click and "Convert Input to Widget" to show a widget instead. Use this when you want the input to default to receiving connections but still allow direct value entry.

> **FLAG - Serialization Behavior:** Inputs with `forceInput: True` or `defaultInput: True` do NOT appear in `widgets_values` in the workflow JSON when they are in input-slot mode. This is the mechanism that prevents certain values from being serialized into the workflow. When a `forceInput` input is connected, the value comes from the upstream node, not from the workflow file. When disconnected, `forceInput` inputs simply have no value (they must be connected or they fail validation if required). See [ComfyUI#9017](https://github.com/Comfy-Org/ComfyUI/issues/9017).

**Source:** [Hidden and Flexible Inputs - ComfyUI Docs](https://docs.comfy.org/custom-nodes/backend/more_on_inputs), [ComfyUI#9017](https://github.com/Comfy-Org/ComfyUI/issues/9017), accessed 2026-02-22

### 2.5 Custom Datatypes

Define custom datatypes by using unique uppercase string identifiers:

```python
# In your provider node:
RETURN_TYPES = ("LLM_PROVIDER",)

# In your generation node:
@classmethod
def INPUT_TYPES(cls):
    return {
        "required": {
            "provider": ("LLM_PROVIDER", {"forceInput": True}),
        }
    }
```

The ComfyUI frontend enforces type matching on connections: an output of type `"LLM_PROVIDER"` can only connect to an input of type `"LLM_PROVIDER"`. Custom types should use `forceInput: True` since there is no built-in widget for arbitrary types.

Custom types are just strings -- there is no registration step. Any unique uppercase string works. Convention is to use uppercase with underscores.

**Source:** [Datatypes - ComfyUI Docs](https://docs.comfy.org/custom-nodes/backend/datatypes), accessed 2026-02-22

### 2.6 Wildcard Inputs and Dynamic Inputs

#### Wildcard Type ("*")

Use `"*"` as the datatype to accept connections from any output type:

```python
"any_input": ("*",),
```

When using wildcards, you must implement `VALIDATE_INPUTS` with an `input_types` parameter to bypass backend type validation:

```python
@classmethod
def VALIDATE_INPUTS(cls, input_types=None, **kwargs):
    # input_types is a dict of {input_name: connected_type}
    # Return True to accept, or error string to reject
    return True
```

Without the `input_types` parameter in `VALIDATE_INPUTS`, ComfyUI's default type checking will reject wildcard connections.

#### Dynamic Inputs (ContainsAnyDict)

For nodes that accept arbitrary keyword arguments:

```python
class AnyDict(dict):
    def __contains__(self, key):
        return True

@classmethod
def INPUT_TYPES(cls):
    return {
        "required": {},
        "optional": AnyDict(),  # Accepts any input name
    }

def execute(self, **kwargs):
    # kwargs contains whatever inputs were connected
    pass
```

This pattern is used by nodes that need to accept a variable number of inputs determined at the frontend level.

**Source:** [Hidden and Flexible Inputs - ComfyUI Docs](https://docs.comfy.org/custom-nodes/backend/more_on_inputs), accessed 2026-02-22

### 2.7 Lazy Evaluation

Lazy inputs are not evaluated until the node explicitly requests them. This enables conditional evaluation -- if a node determines it does not need a particular input, the upstream subgraph for that input never executes.

```python
@classmethod
def INPUT_TYPES(cls):
    return {
        "required": {
            "condition": ("BOOLEAN", {"default": True}),
            "value_if_true": ("STRING", {"lazy": True}),
            "value_if_false": ("STRING", {"lazy": True}),
        }
    }

def check_lazy_status(self, condition, value_if_true=None, value_if_false=None):
    # Return list of input names that still need evaluation
    needed = []
    if condition and value_if_true is None:
        needed.append("value_if_true")
    elif not condition and value_if_false is None:
        needed.append("value_if_false")
    return needed  # Empty list = all needed inputs are ready

def execute(self, condition, value_if_true=None, value_if_false=None):
    return (value_if_true if condition else value_if_false,)
```

`check_lazy_status` is called repeatedly. Each call returns a list of input names that need evaluation. When it returns an empty list, the FUNCTION method is called.

**Source:** [Lazy Evaluation - ComfyUI Docs](https://docs.comfy.org/custom-nodes/backend/lazy_evaluation), accessed 2026-02-22

### 2.8 Optional Input Handling in Python

Optional inputs that are not connected are simply not passed to the function. Use default parameter values:

```python
def execute(self, required_input, optional_input=None):
    if optional_input is not None:
        # Use it
        pass
```

Or use `**kwargs`:

```python
def execute(self, **kwargs):
    optional = kwargs.get("optional_input", None)
```

---

## 3. Output System

### 3.1 RETURN_TYPES and RETURN_NAMES

```python
RETURN_TYPES = ("STRING", "BOOLEAN")      # Types of each output
RETURN_NAMES = ("text", "success")        # Display labels (optional)
```

- `RETURN_TYPES` is a tuple of type strings. Trailing comma required for single outputs: `("STRING",)`.
- `RETURN_NAMES` defaults to lowercase versions of `RETURN_TYPES` if omitted.
- The FUNCTION method must return a **tuple** matching `RETURN_TYPES` in length and order.

```python
def execute(self, prompt):
    result = "generated text"
    return (result,)  # Note the trailing comma for single-element tuple
```

### 3.2 Data Flow

Output data from one node flows to connected input nodes via their connection links. Each output slot produces one value that can fan out to multiple downstream inputs. ComfyUI handles the routing -- the node just returns a tuple.

### 3.3 Batch/List Behavior

ComfyUI internally represents data flowing between nodes as a **Python list**, typically of length 1. When multiple data instances need processing, the list contains multiple items.

**Key distinction:** A **batch** (e.g., a tensor with batch dimension `[B,H,W,C]`) is a single entry in the list. A **list** may contain multiple batches.

#### Default Behavior (Auto-Iteration)

By default, ComfyUI auto-iterates over list inputs:

- The FUNCTION method is called **once for each value** in the input lists
- If input lists have different lengths, shorter ones are **padded by repeating the last value**
- Output results are collected into lists matching the longest input's length

This is implemented in `map_node_over_list` in `execution.py`.

#### OUTPUT_IS_LIST

When a node returns a Python list as one of its outputs, ComfyUI normally wraps it as a single data item. To instead treat the list as multiple sequential items:

```python
OUTPUT_IS_LIST = (True,)  # Tuple of bools matching RETURN_TYPES length
```

#### INPUT_IS_LIST

To receive the complete list in a single call instead of auto-iterating:

```python
INPUT_IS_LIST = True
```

**Important limitation:** `INPUT_IS_LIST` is node-level, not per-input. When True, **all** inputs arrive as lists, including widget values. You must index widget values with `[0]`:

```python
class MyListNode:
    INPUT_IS_LIST = True
    OUTPUT_IS_LIST = (True,)

    def execute(self, images, batch_size):
        batch_size = batch_size[0]  # Widget values are also lists now
        # ... process list of images ...
        return (output_list,)
```

**Source:** [Data Lists - ComfyUI Docs](https://docs.comfy.org/custom-nodes/backend/lists), accessed 2026-02-22

### 3.4 OUTPUT_NODE

When `OUTPUT_NODE = True`:

- The node executes even if no downstream node consumes its outputs
- It appears as a terminal/output node in the execution graph
- The UI shows execution controls on the node

Set this for any node whose purpose is a **side effect** (displaying results, saving files, sending data to external services) rather than producing data for other nodes.

Without `OUTPUT_NODE = True`, a node only executes if its outputs are consumed by at least one other node in the active graph.

---

## 4. Error Handling & User Feedback

### 4.1 Exception Handling

When a node's FUNCTION raises an unhandled exception:

| Aspect | Behavior |
|--------|----------|
| Workflow | **Halts entirely.** No remaining nodes execute. |
| UI feedback | Failed node gets **red outline**. Error message displayed in UI notification. |
| Console | Full traceback logged to server console. |
| WebSocket | `execution_error` message sent with `node_id`, `node_type`, `exception_type`, `exception_message` |
| Cleanup | None. Already-executed nodes retain their cached outputs. |
| Recovery | User must fix the issue and re-queue the workflow. |

There is **no built-in mechanism** for a node to catch errors from other nodes, resume execution from a specific point, or implement per-branch error isolation. This is a known limitation.

**Source:** [ComfyUI Discussion #3643](https://github.com/comfyanonymous/ComfyUI/discussions/3643), [ComfyUI#11048](https://github.com/Comfy-Org/ComfyUI/issues/11048), accessed 2026-02-22

### 4.2 VALIDATE_INPUTS

`VALIDATE_INPUTS` is a `@classmethod` called **before** workflow execution during the validation phase. It does not run during execution itself.

```python
@classmethod
def VALIDATE_INPUTS(cls, **kwargs):
    # Return True if valid
    # Return error string if invalid
    if not some_condition:
        return "Error: required file not found"
    return True
```

**Key behaviors:**

- Receives only **constant** (widget) inputs, not values from connected nodes
- To validate connected input types, accept an `input_types` parameter:
  ```python
  @classmethod
  def VALIDATE_INPUTS(cls, input_types=None, **kwargs):
      if input_types and input_types.get("my_input") != "EXPECTED_TYPE":
          return "Wrong input type"
      return True
  ```
- When validation fails, the UI shows "Failed to validate prompt for output X: Custom validation failed for node: [field] - [error message]"
- The workflow does not execute at all if any node fails validation
- With `**kwargs`, the method can accept any set of inputs without raising TypeError on unexpected arguments

**Source:** [Properties - ComfyUI Docs](https://docs.comfy.org/custom-nodes/backend/server_overview), accessed 2026-02-22

### 4.3 Logging

Custom nodes can log to ComfyUI's console output using standard Python logging:

```python
import logging
logger = logging.getLogger(__name__)

def execute(self, **kwargs):
    logger.info("Processing request...")
    logger.warning("Parameter X unsupported for this backend, ignoring")
    logger.error("API returned error: %s", error_msg)
```

Or simply use `print()`, which goes to the server console.

### 4.4 UI Communication from Nodes

#### PromptServer.send_sync (Python to JavaScript)

Nodes can send messages to the frontend during execution:

```python
from server import PromptServer

def execute(self, **kwargs):
    # Send a custom message to the frontend
    PromptServer.instance.send_sync(
        "my_pack.event_name",      # Unique event type string
        {"message": "Processing complete", "status": "ok"}
    )
    return (result,)
```

Frontend JavaScript receives these via event listeners (see Section 6).

#### Progress Reporting

For long-running operations, use `comfy.utils.ProgressBar`:

```python
import comfy.utils

def execute(self, **kwargs):
    pbar = comfy.utils.ProgressBar(total_steps)
    for i in range(total_steps):
        # ... do work ...
        pbar.update(1)
    return (result,)
```

This integrates with ComfyUI's WebSocket progress system and shows a progress bar in the UI. The progress information is broadcast via WebSocket `progress` messages with `value` and `max` fields.

**Source:** [Getting Started - ComfyUI Docs](https://docs.comfy.org/custom-nodes/walkthrough), [ComfyUI#1936](https://github.com/comfyanonymous/ComfyUI/issues/1936), accessed 2026-02-22

### 4.5 Returning UI Data

Nodes can return extra data for the UI alongside their outputs. This is done by including a `ui` key in the return dict:

```python
def execute(self, images):
    # Normal output processing...
    result = process(images)

    # Return both output data and UI data
    return {"ui": {"text": ["Some status message"]}, "result": (result,)}
```

The `ui` dict is sent to the frontend and can be used by JavaScript extensions to display information. The built-in `SaveImage` and `PreviewImage` nodes use this to send image previews back to the frontend.

> **FLAG - Documentation Gap:** The exact format and capabilities of the `ui` return dict are not well-documented in official docs. The pattern is used by built-in preview/save nodes. The V3 spec provides better UI helpers (see Section 10).

---

## 5. Image/Tensor Handling

### 5.1 IMAGE Type

| Property | Value |
|----------|-------|
| Shape | `[B, H, W, C]` (Batch, Height, Width, Channels) |
| Channels | 3 (RGB) |
| Dtype | `torch.float32` |
| Value range | 0.0 to 1.0 |
| Batch dimension | **Always present**, even for single images |

The batch dimension is always present. A single image has shape `[1, H, W, C]`. This is a common source of bugs -- some operations squeeze the batch dimension, producing `[H, W, C]`, which breaks downstream nodes.

```python
# Ensure batch dimension exists
if image.dim() == 3:  # [H, W, C]
    image = image.unsqueeze(0)  # -> [1, H, W, C]
```

### 5.2 MASK Type

| Property | Value |
|----------|-------|
| Shape | `[H, W]` or `[B, C, H, W]` |
| Dtype | `torch.float32` |
| Value range | 0.0 to 1.0 (normalized) |

> **FLAG - Ambiguity:** The docs list two possible shapes for MASK. In practice, most nodes expect `[H, W]` for single masks and `[B, H, W]` for batched masks, but the exact convention varies across built-in nodes and custom packs. Check the specific context.

### 5.3 LATENT Type

| Property | Value |
|----------|-------|
| Python type | `dict` with key `"samples"` |
| Shape of `samples` | `[B, C, H, W]` |
| Channels | 4 (latent channels) |
| H, W | 1/8 of the original image dimensions |

```python
latent = {"samples": torch.randn(1, 4, 64, 64)}  # 512x512 image in latent space
```

### 5.4 AUDIO Type

| Property | Value |
|----------|-------|
| Python type | `dict` with keys `"waveform"` and `"sample_rate"` |
| Shape of `waveform` | `[B, C, T]` (Batch, Channels, Time) |

### 5.5 Other Built-in Types

| Type | Python Representation | Notes |
|------|-----------------------|-------|
| `MODEL` | Diffusion model object | Opaque to most custom nodes |
| `CLIP` | CLIP model object | Text encoding |
| `VAE` | VAE model object | Encode/decode between pixel and latent space |
| `CONDITIONING` | List of tuples | `[(cond_tensor, {"pooled_output": pooled})]` |
| `NOISE` | Object with `generate_noise(input_latent) -> Tensor` | Optional `seed` property |
| `SAMPLER` | Object with `sample` method | Sampling algorithm |
| `SIGMAS` | 1D tensor, length `steps+1` | Noise schedule levels |

These types are primarily used by diffusion pipeline nodes. Custom nodes that don't interact with the diffusion pipeline rarely need them, but they are valid connection types.

**Source:** [Datatypes - ComfyUI Docs](https://docs.comfy.org/custom-nodes/backend/datatypes), accessed 2026-02-22

### 5.6 Conversion Patterns

#### IMAGE Tensor to PIL

```python
import numpy as np
from PIL import Image

# image shape: [B, H, W, C], float32, range [0,1]
# Process single image from batch:
image_np = (255.0 * image[0].cpu().numpy()).clip(0, 255).astype(np.uint8)
pil_image = Image.fromarray(image_np)
```

#### IMAGE Tensor to Base64

```python
import base64
import io
import numpy as np
from PIL import Image

def tensor_to_base64(image_tensor, format="PNG"):
    """Convert a single image tensor [H,W,C] to base64 string."""
    image_np = (255.0 * image_tensor.cpu().numpy()).clip(0, 255).astype(np.uint8)
    pil_image = Image.fromarray(image_np)
    buffered = io.BytesIO()
    pil_image.save(buffered, format=format)
    return base64.b64encode(buffered.getvalue()).decode("utf-8")

# For a batch [B,H,W,C]:
for i in range(image_batch.shape[0]):
    b64 = tensor_to_base64(image_batch[i])
```

#### PIL to IMAGE Tensor

```python
import torch
import numpy as np
from PIL import Image

pil_image = Image.open("image.png").convert("RGB")
image_np = np.array(pil_image).astype(np.float32) / 255.0
image_tensor = torch.from_numpy(image_np).unsqueeze(0)  # [1, H, W, C]
```

### 5.7 Common Pitfalls

1. **Missing batch dimension**: Always check `.dim()` and `unsqueeze(0)` if needed.
2. **Wrong dtype**: ComfyUI expects `float32` in range `[0,1]`. Don't pass `uint8` or unnormalized values.
3. **Channel order**: ComfyUI uses `[B,H,W,C]` (channels last), NOT PyTorch's typical `[B,C,H,W]` (channels first). Permute if needed: `tensor.permute(0, 3, 1, 2)` for channels-first, or `tensor.permute(0, 2, 3, 1)` for channels-last.
4. **Squeezed tensors**: Some torch operations collapse the batch dimension. Always verify shape after operations.
5. **Device mismatch**: Convert to CPU before numpy operations: `tensor.cpu().numpy()`.

### 5.8 Batch Processing in Workflows

ComfyUI does NOT auto-iterate over the batch dimension of IMAGE tensors. A batch of images `[B,H,W,C]` flows as a **single data item** through the graph. Individual nodes must handle the batch dimension themselves (iterate over `image[i]` for each image in the batch).

The auto-iteration behavior (Section 3.3) operates on the **list** level, not the batch dimension level. A list of two image batches `[list_item_1: [3,H,W,C], list_item_2: [2,H,W,C]]` would cause the node to execute twice (once per list item), but each execution receives the full batch tensor.

**Source:** [Tensors - ComfyUI Docs](https://docs.comfy.org/custom-nodes/backend/tensors), [Data Lists - ComfyUI Docs](https://docs.comfy.org/custom-nodes/backend/lists), accessed 2026-02-22

---

## 6. Frontend JavaScript

### 6.1 Extension Registration

```javascript
import { app } from "../../scripts/app.js";

app.registerExtension({
    name: "unique.extension.name",  // Globally unique identifier

    // === Lifecycle Hooks (in execution order) ===

    async init() {
        // Page load, after graph creation, before node registration.
        // Can hijack core behavior -- increases incompatibility risk.
    },

    // addCustomNodeDefs -- custom node definition registration

    getCustomWidgets(app) {
        // Register custom widget types. Return object mapping type names
        // to constructor functions.
        return {};
    },

    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        // Called once per node type before registration.
        // Modify nodeType.prototype to affect ALL instances of this node type.
        // Most commonly used hook -- often the only one needed.
        // Check nodeType.comfyClass to target specific nodes.
    },

    // registerCustomNodes -- completion of node registration

    async nodeCreated(node) {
        // Called when an individual node instance is created.
        // For instance-specific modifications.
    },

    async setup() {
        // Startup complete. Add event listeners, global menu modifications.
        // Do NOT use for workflow-loaded actions -- use afterConfigureGraph instead.
    },

    // === Workflow Loading Hooks ===
    async beforeConfigureGraph(graphData) {},
    async loadedGraphNode(node, graphData) {},
    async afterConfigureGraph(graphData) {},
});
```

#### Complete Hook Execution Order

**Page load:** `init` -> `addCustomNodeDefs` -> `getCustomWidgets` -> `beforeRegisterNodeDef` (per node type) -> `registerCustomNodes` -> `beforeConfigureGraph` -> `nodeCreated` (per node) -> `loadedGraphNode` (per node) -> `afterConfigureGraph` -> `setup`

**Loading workflow:** `beforeConfigureGraph` -> `beforeRegisterNodeDef` (optional, for new types) -> `nodeCreated` (per node) -> `loadedGraphNode` (per node) -> `afterConfigureGraph`

**Adding new node:** `nodeCreated`

**Source:** [JavaScript Hooks - ComfyUI Docs](https://docs.comfy.org/custom-nodes/js/javascript_hooks), [JavaScript Objects and Hijacking - ComfyUI Docs](https://docs.comfy.org/custom-nodes/js/javascript_objects_and_hijacking), accessed 2026-02-22

### 6.2 WEB_DIRECTORY

Set in `__init__.py`:

```python
WEB_DIRECTORY = "./web"     # Convention 1
WEB_DIRECTORY = "./web/js"  # Convention 2 (from scaffold tool)
WEB_DIRECTORY = "./js"      # Convention 3
```

All three are valid. Files in this directory are auto-served by ComfyUI. The `comfy node scaffold` tool uses `"./web/js"` by default.

### 6.3 Key Node Properties (JavaScript)

| Property | Type | Purpose |
|----------|------|---------|
| `node.id` | number | Unique identifier |
| `node.type` | string | Node class name |
| `node.comfyClass` | string | Python class name (use for identification) |
| `node.widgets` | array | Widget instances |
| `node.inputs` | array | Input slot definitions |
| `node.outputs` | array | Output slot definitions |
| `node.size` | [w, h] | Canvas dimensions |
| `node.pos` | [x, y] | Canvas position |
| `node.mode` | number | 0=normal, 2=muted, 4=bypassed |
| `node.flags.collapsed` | bool | Collapsed state |
| `node.properties` | object | Properties dict (Properties Panel) |
| `node.serialize_widgets` | bool | Enable widget serialization (default: true) |
| `node.graph` | LGraph | Reference to parent graph |

### 6.4 Node Callbacks

Set these on the prototype via `beforeRegisterNodeDef`:

```javascript
async beforeRegisterNodeDef(nodeType, nodeData, app) {
    if (nodeType.comfyClass === "MyNode") {
        const origOnNodeCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function() {
            origOnNodeCreated?.apply(this, arguments);
            // Custom initialization here
        };
    }
}
```

| Callback | Purpose |
|----------|---------|
| `onNodeCreated()` | Instance initialization, widget setup |
| `onConfigure(info)` | Restore saved state on graph load |
| `onSerialize(info)` | Save extra state beyond widget values |
| `onConnectionChange(side)` | React to connections added/removed (side=1 for input) |
| `getExtraMenuOptions(canvas, options)` | Add right-click menu items |
| `onDrawForeground(ctx)` | Custom rendering overlay (decorative only -- see note) |
| `onDrawBackground(ctx)` | Background rendering |
| `onMouseDown/Move/Up(e, pos, canvas)` | Mouse events |
| `onDblClick(e, pos, canvas)` | Double click |
| `onPropertyChanged(name, value)` | Property Panel change |
| `onResize(size)` | Node resized |

**Note on `onDrawForeground`**: Fires BEFORE slots and widgets are drawn. Custom foreground content can be painted over by the framework. Appropriate only for decorative overlays (badges, status indicators). For interactive custom UI, use a custom widget with `draw()` and `mouse()` methods instead.

### 6.5 JS-Python Communication

#### Python to JavaScript (via PromptServer.send_sync)

**Python side:**
```python
from server import PromptServer

PromptServer.instance.send_sync(
    "mypack.event_name",
    {"key": "value", "node_id": unique_id}
)
```

**JavaScript side:**
```javascript
import { api } from "../../scripts/api.js";

api.addEventListener("mypack.event_name", (event) => {
    const data = event.detail;
    console.log(data.key);  // "value"
});
```

#### JavaScript to Python (via Custom API Endpoints)

See Section 7 for registering custom HTTP endpoints.

**JavaScript side:**
```javascript
import { api } from "../../scripts/api.js";

async function fetchModels(provider, url) {
    const body = new FormData();
    body.append('provider', provider);
    body.append('url', url);
    const response = await api.fetchApi("/mypack/models", {
        method: "POST",
        body,
    });
    return await response.json();
}
```

### 6.6 Dynamic Widget Modification

#### Adding Widgets

```javascript
// Standard built-in widget
node.addWidget("combo", "model", "default_model", (value) => {
    console.log("Selected:", value);
}, { values: ["model_a", "model_b"] });

// Custom widget object
node.addCustomWidget(myWidgetInstance);

// DOM element as widget
node.addDOMWidget("name", "type", domElement, options);
```

#### Updating COMBO Widget Values Dynamically

```javascript
const widget = node.widgets.find(w => w.name === "model");
if (widget) {
    widget.options.values = ["new_model_a", "new_model_b"];
    widget.value = widget.options.values[0];
}
```

#### After Dynamic Changes

Always recalculate size and trigger a redraw after modifying widgets:

```javascript
node.setSize(node.computeSize());
node.graph?.setDirtyCanvas(true, true);
```

### 6.7 Widget Serialization Rules

- Widget `name` must match the Python `INPUT_TYPES` key exactly for the value to reach the backend
- Widget order in `node.widgets` matches `widgets_values` order in serialized workflow
- `serializeValue(node, index)` can override default serialization
- Suppress serialization with `options = { serialize: false }` for UI-only widgets (dividers, spacers)
- **Widget value must NEVER be an array** -- arrays in ComfyUI's widget system signal a node connection/link. For multi-value storage, use an object: `value = { values: [1, 2, 3] }`
- Custom widgets added via `addCustomWidget()` serialize to `widgets_values` automatically -- no hidden backend widget is needed

### 6.8 Widget Interface (Custom Widgets)

Custom widgets are objects with optional methods called by the framework:

| Property/Method | Signature | Purpose |
|-----------------|-----------|---------|
| `name` | string | Unique identifier within the node (must match INPUT_TYPES key) |
| `type` | string | `"number"`, `"combo"`, `"toggle"`, `"custom"`, etc. |
| `value` | any | Current value. **Must NOT be an array** (arrays signal a link) |
| `options` | object | `{default, min, max, step, serialize, hidden}` |
| `callback` | function | Called on value change |
| `y` | number | Top of widget row (set by framework `arrange()`) |
| `last_y` | number | Same as `y`, used for mouse bounds checking |
| `draw(ctx, node, width, posY, height)` | function | Custom rendering. `posY` is absolute canvas Y. |
| `mouse(event, pos, node)` | function | Handle pointer events. Return `true` to consume. |
| `computeSize(width)` | function | Returns `[w, h]` to override default widget height. |
| `computeLayoutSize(node)` | function | Returns `{minHeight, maxHeight, minWidth}` for dynamic height. |
| `serializeValue(node, index)` | function | Custom serialization logic. |

**draw() coordinate system:**
- `posY` is absolute canvas Y, NOT node-relative
- Use `15` for left margin, `width - 15` for right margin
- `ctx` is already in canvas space -- draw directly

**mouse() coordinate system:**
- `pos[0]` = absolute canvas X
- `pos[1]` = absolute canvas Y
- Compare `pos[0]` against `node.size[0]` for width bounds
- Compare `pos[1]` against `this.last_y` for Y bounds

> **FLAG - Documentation Gap:** The full `addCustomWidget()` interface and the widget `draw()`/`mouse()` methods are not in official docs. This interface is stable in practice and used by major custom node packs (rgthree, pythongosssss), but must be learned from source code.

### 6.9 Deprecated Patterns

The following are explicitly deprecated in the official docs:

1. **Monkey-patching `app` or `LGraphCanvas.prototype`** -- Use extension hooks and `beforeRegisterNodeDef` callbacks instead
2. **Hijacking context menus via prototype** -- Use the official Context Menu API instead
3. **Manual Y position calculations for widgets/slots** -- The slot formula uses `(filteredIndex + 0.7) * SLOT_HEIGHT` where filteredIndex skips hidden slots; manual calcs are always approximate and fragile
4. **Force-setting `widget.type = "converted-widget"`** -- Meant for user-initiated conversion only

**Correct alternatives:** Custom widgets with `draw()`/`mouse()` methods, extension hooks, `beforeRegisterNodeDef` callbacks.

**Source:** [JavaScript Objects and Hijacking - ComfyUI Docs](https://docs.comfy.org/custom-nodes/js/javascript_objects_and_hijacking), accessed 2026-02-22

### 6.10 API Events

```javascript
import { api } from "../../scripts/api.js";

// Execution lifecycle events
api.addEventListener("execution_start", ({detail}) => { /* prompt started */ });
api.addEventListener("executing", ({detail}) => { /* node currently executing */ });
api.addEventListener("executed", ({detail}) => { /* node finished */ });
api.addEventListener("execution_cached", ({detail}) => { /* cached results used */ });
api.addEventListener("progress", ({detail}) => { /* progress update: value, max */ });
api.addEventListener("status", ({detail}) => { /* queue status change */ });
```

### 6.11 Prompt Structure (graphToPrompt)

The `app.graphToPrompt()` method returns:

**output**: Maps `node_id` to objects containing:
- `class_type` -- Python class identifier
- `inputs` -- Widget values or arrays `[upstream_node_id, slot_index]` for connections

**workflow**: Contains:
- `nodes` -- Array with: `id`, `type`, `pos`, `size`, `mode`, `flags`, `widgets_values`, `inputs`, `outputs`
- `links` -- Array format: `[link_id, source_id, source_slot, target_id, target_slot, type_string]`
- `groups`, `version`, `config`, `extra` metadata

**Source:** [JavaScript Objects and Hijacking - ComfyUI Docs](https://docs.comfy.org/custom-nodes/js/javascript_objects_and_hijacking), accessed 2026-02-22

---

## 7. Custom API Endpoints

### 7.1 Registering Custom HTTP Endpoints

Custom nodes can register HTTP endpoints that the frontend (or external clients) can call:

```python
from server import PromptServer
from aiohttp import web

routes = PromptServer.instance.routes

@routes.get('/mypack/models')
async def get_models(request):
    provider = request.query.get('provider', '')
    url = request.query.get('url', '')

    # Query the backend for available models
    models = await fetch_model_list(provider, url)

    return web.json_response({"models": models})

@routes.post('/mypack/config')
async def update_config(request):
    data = await request.json()
    # Process the config update
    return web.json_response({"status": "ok"})
```

**Key points:**

- Route handlers are **module-level functions**, not class methods. They are registered when the module is imported (at ComfyUI startup).
- Use `@routes.get()` for read operations, `@routes.post()` for mutations.
- Handlers are **async functions** that receive an aiohttp `request` object.
- Return `web.json_response()` for JSON, `web.Response()` for other content types.
- These handlers run on the main asyncio event loop, so `await` works normally here (unlike inside node FUNCTION methods).

### 7.2 Frontend Calling Custom Endpoints

```javascript
import { api } from "../../scripts/api.js";

// Using api.fetchApi (adds ComfyUI headers automatically)
const response = await api.fetchApi(
    "/mypack/models?provider=ollama&url=localhost:11434"
);
const data = await response.json();

// Using FormData for POST
const body = new FormData();
body.append('key', 'value');
await api.fetchApi("/mypack/config", { method: "POST", body });
```

### 7.3 Common Use Case: Dynamic Model Dropdown

The most common use case for custom endpoints is populating a COMBO widget with dynamic data (e.g., model list from a running backend):

1. Python endpoint queries the backend's model list API (e.g., Ollama's `/api/tags`)
2. Frontend JS calls this endpoint when the provider or URL widget changes
3. JS updates the COMBO widget's `options.values` with the fetched list

This is the pattern used by comfyui-ollama for its model dropdown.

### 7.4 Built-in Server Endpoints

ComfyUI's server provides ~30+ built-in routes:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/prompt` | GET/POST | Queue submission and status retrieval |
| `/queue` | GET/POST | Queue state management |
| `/interrupt` | POST | Halt current execution |
| `/history` | GET | Workflow execution history |
| `/models/{folder}` | GET | Model discovery and retrieval |
| `/object_info` | GET | Node type details and specifications |
| `/upload/image` | POST | Asset upload |
| `/system_stats` | GET | Device and performance metrics |
| `/ws` | WebSocket | Bidirectional real-time communication |

### 7.5 Security Considerations

- Custom endpoints run with the same permissions as the ComfyUI server
- There is no built-in authentication for custom routes
- Endpoints are accessible to anyone who can reach the ComfyUI server
- Do not expose API keys or sensitive configuration through custom endpoints

**Source:** [Routes - ComfyUI Docs](https://docs.comfy.org/development/comfyui-server/comms_routes), accessed 2026-02-22

---

## 8. Configuration & Secrets

### 8.1 Workflow JSON Serialization

ComfyUI serializes workflow state to JSON files. Understanding what gets serialized is critical for security.

#### What Gets Serialized

Per node:
- `id`, `type`, `pos`, `size`, `mode`, `order`, `flags`
- `widgets_values`: Array or object containing the current value of every widget
- `inputs`/`outputs`: Socket definitions with connection references
- `properties`: Node properties dict

**The critical security concern:** Every widget value is serialized into `widgets_values`. If an API key is a regular STRING widget, **it will be saved in the workflow JSON** and can leak when the workflow is shared.

#### What Does NOT Get Serialized

- Inputs with `forceInput: True` that are in connection-slot mode (no widget exists to serialize)
- Hidden inputs (they are server-provided, not stored in workflow)
- Widgets with `options.serialize = false` on the JS side

### 8.2 Preventing API Key Serialization

Three mechanisms to keep sensitive data out of workflow JSON:

1. **External config file** (strongest): Read API keys from a config file or environment variables at runtime. The node never receives the key as an input -- it reads it directly from the config during execution. The key never touches the ComfyUI input/output system at all.

2. **forceInput: True**: Make the API key input a connection-only slot. The key value never exists as a widget, so it cannot be serialized. The key must come from another node.

3. **Hidden inputs**: Use the `hidden` input category. These values are server-provided and never appear in the UI or workflow JSON. Limited to the predefined hidden types (UNIQUE_ID, PROMPT, etc.) unless you create a custom mechanism.

### 8.3 Config File Conventions

Observed conventions in the ecosystem:

| Location | Used By | Pros | Cons |
|----------|---------|------|------|
| Node pack directory (`config.yaml`) | Most common pattern (comfyui_controlnet_aux, etc.) | Simple, portable, self-contained | May not survive updates that replace the directory |
| ComfyUI user directory (`user/default/PackName/config.ini`) | ComfyUI-Manager | Survives node pack updates | More complex path resolution |
| Environment variables | CI/deployment scenarios | Standard practice, no files to manage | Not user-friendly for desktop users |

**Recommended pattern:** Ship `config.example.yaml` in the repo, user copies to `config.yaml` (gitignored). Resolution order: `config.yaml` -> environment variables -> defaults.

### 8.4 API Key Resolution Pattern

```python
import os
import yaml

def get_api_key(provider: str, config: dict) -> str | None:
    """Resolution chain: config.yaml -> env var -> None"""
    # 1. Check config file
    key = config.get("providers", {}).get(provider, {}).get("api_key")
    if key:
        return key

    # 2. Check environment variable
    env_var_map = {
        "openai": "OPENAI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "gemini": "GEMINI_API_KEY",
    }
    env_var = env_var_map.get(provider)
    if env_var:
        key = os.environ.get(env_var)
        if key:
            return key

    # 3. None (acceptable for local backends)
    return None
```

### 8.5 Environment Variable Access

Standard `os.environ` access works from within node code. No special ComfyUI mechanism is needed:

```python
import os

api_key = os.environ.get("OPENAI_API_KEY")
```

### 8.6 Security Notes

- The ComfyUI ecosystem experienced security incidents in early 2025 involving malicious custom nodes that exfiltrated API keys and credentials
- Never log or print API keys
- Never expose keys through custom API endpoints
- Store keys outside the workflow graph
- Warn users about key security in documentation

**Source:** [Workflow JSON Spec](https://docs.comfy.org/specs/workflow_json), [ComfyUI#9017](https://github.com/Comfy-Org/ComfyUI/issues/9017), accessed 2026-02-22

---

## 9. Publishing & Distribution

### 9.1 Two Publishing Paths

#### ComfyUI Registry (Modern, Recommended)

1. Create publisher ID at [registry.comfy.org](https://registry.comfy.org)
2. Add `pyproject.toml` with `[tool.comfy]` section
3. Publish via GitHub Action or CLI

**Required `pyproject.toml`:**

```toml
[project]
name = "comfyui-my-node-pack"
version = "1.0.0"
description = "Description of the node pack"
license = { text = "MIT" }
requires-python = ">= 3.10"
dependencies = [
    "aiohttp>=3.8.0",
    "pyyaml>=6.0",
]

[project.urls]
Repository = "https://github.com/username/comfyui-my-node-pack"

[tool.comfy]
PublisherId = "your-publisher-id"
DisplayName = "My Node Pack"
Icon = ""
```

**`pyproject.toml` fields:**

| Section | Field | Required | Notes |
|---------|-------|----------|-------|
| `[project]` | `name` | Yes | Unique ID, <100 chars, alphanumeric + hyphens/underscores/periods |
| `[project]` | `version` | Yes | SemVer format (X.Y.Z) |
| `[project]` | `description` | Recommended | Brief explanation |
| `[project]` | `license` | Recommended | `{ text = "MIT" }` or `{ file = "LICENSE" }` |
| `[project]` | `requires-python` | Recommended | e.g., `">= 3.10"` |
| `[project]` | `dependencies` | If needed | Runtime dependencies |
| `[project]` | `classifiers` | Optional | OS compatibility, GPU support |
| `[project.urls]` | `Repository` | Yes | GitHub URL |
| `[tool.comfy]` | `PublisherId` | Yes | Your registry publisher ID |
| `[tool.comfy]` | `DisplayName` | Optional | Human-readable name |
| `[tool.comfy]` | `Icon` | Optional | Image URL, max 400x400, square |
| `[tool.comfy]` | `requires-comfyui` | Optional | Version constraints |

**GitHub Action (`publish.yml`):**

```yaml
name: Publish to Comfy registry
on:
  workflow_dispatch:
  push:
    branches:
      - main
    paths:
      - "pyproject.toml"

jobs:
  publish-node:
    name: Publish Custom Node to registry
    runs-on: ubuntu-latest
    steps:
      - name: Check out code
        uses: actions/checkout@v4
      - name: Publish Custom Node
        uses: Comfy-Org/publish-node-action@v1
        with:
          personal_access_token: ${{ secrets.REGISTRY_ACCESS_TOKEN }}
```

Store your registry access token as a repository secret named `REGISTRY_ACCESS_TOKEN`. The workflow publishes when you push an update to your `pyproject.toml`'s `version` field.

**Source:** [Registry Specifications](https://docs.comfy.org/registry/specifications), [publish-node-action](https://github.com/Comfy-Org/publish-node-action), accessed 2026-02-22

#### ComfyUI Manager (Legacy)

1. Host your node pack as a git repository
2. Submit a PR to the ComfyUI Manager repo editing `custom-node-list.json`
3. Manager clones repo, runs `pip install -r requirements.txt`, then `install.py`

**Source:** [Publishing to Manager - ComfyUI Docs](https://docs.comfy.org/custom-nodes/backend/manager), accessed 2026-02-22

### 9.2 Lifecycle Scripts

| Script | When Executed | Notes |
|--------|---------------|-------|
| `install.py` | After pip install on initial setup | Runs from repo root. For non-pip setup tasks. |
| `uninstall.py` | On uninstall | May not run if user manually deletes the directory |
| `disable.py` | When user disables node | Directory gets `.disabled` suffix appended |
| `enable.py` | When user re-enables node | Only runs on re-enable, not initial install |

### 9.3 requirements.txt Best Practices

- Use **permissive versioning** (no strict version pins) to avoid conflicts with other node packs
- Only list net-new dependencies, not things already in ComfyUI (torch, numpy, PIL, etc.)
- Example: `aiohttp>=3.8.0` not `aiohttp==3.11.2`

### 9.4 What Makes a Well-Behaved Node Pack

1. **Unique node names**: Prefix `NODE_CLASS_MAPPINGS` keys with your pack name to avoid collisions
2. **Grouped categories**: Use a top-level category for your pack, subcategories within
3. **Minimal dependencies**: Don't pull in heavy libraries users don't need
4. **Permissive version pins**: Don't break other packs with strict pins
5. **Clean error handling**: Catch exceptions internally, log useful messages
6. **Config file security**: Never serialize API keys into workflow JSON
7. **Documentation**: Include help pages (see Section 9.5)

### 9.5 Help Page System

ComfyUI supports rich markdown documentation per node:

1. Create a `docs/` folder inside your `WEB_DIRECTORY`
2. Name files after `NODE_CLASS_MAPPINGS` keys: `MyNodeName.md`
3. Support locales: `MyNodeName/en.md`, `MyNodeName/zh.md`, etc.
4. Supports standard markdown, images, and `<video>` elements
5. If you add `tooltip` to your input parameters, those are automatically shown in the help system

**Source:** [Help Page - ComfyUI Docs](https://docs.comfy.org/custom-nodes/help_page), accessed 2026-02-22

---

## 10. V3 Node Specification

### 10.1 Current Status

V3 is the actively developed node schema. As of early 2026:

- The API follows a versioning system: `comfy_api.latest` points to the newest API under development
- The first API version is `v0_0_2`, which is subject to change without warning
- Once stabilized, a `v0_0_3` will be created and `v0_0_2` becomes stable
- Multiple built-in ComfyUI nodes (String nodes, Google Veo, Ideogram, AudioEncoder) have been migrated to V3
- Future node features will **only** be added to V3 schema

**There is no explicit deprecation timeline for V1.** V1 nodes continue to work, but new features (like native Vue widget support) are V3-only.

### 10.2 Key Differences from V1

| Aspect | V1 | V3 |
|--------|----|----|
| Base class | Any class | `io.ComfyNode` |
| Input definition | `INPUT_TYPES()` dict | `io.Schema` with typed input objects |
| Output definition | `RETURN_TYPES` tuple | `outputs` list in Schema |
| Execution method | Any name (FUNCTION) | Always `execute` (classmethod) |
| Return type | Tuple | `io.NodeOutput` |
| State | Instance variables (`self`) | **No instance state** -- classmethods only |
| Registration | `NODE_CLASS_MAPPINGS` dict | `comfy_entrypoint()` -> `ComfyExtension` |
| Cache control | `IS_CHANGED()` | `fingerprint_inputs()` |
| Validation | `VALIDATE_INPUTS()` | `validate_inputs()` |
| Hidden inputs | String constants in dict | `io.Hidden.unique_id`, etc. |
| Lazy evaluation | `check_lazy_status()` instance method | `check_lazy_status()` async classmethod |

### 10.3 V3 Node Example

```python
from comfy_api.latest import io, ComfyExtension

class MyNode(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="MyPack_MyNode",      # Globally unique, use prefix
            display_name="My Node",
            category="MyPack",
            inputs=[
                io.String.Input("prompt", multiline=True),
                io.Float.Input("temperature", default=0.7, min=0.0, max=2.0),
                io.Image.Input("image", optional=True),
            ],
            outputs=[
                io.String.Output(display_name="result"),
                io.Boolean.Output(display_name="success"),
            ],
            is_output_node=False,
        )

    @classmethod
    def execute(cls, prompt, temperature, image=None) -> io.NodeOutput:
        result = do_something(prompt, temperature, image)
        return io.NodeOutput(result, True)

# Registration
class MyExtension(ComfyExtension):
    async def get_node_list(self) -> list[type[io.ComfyNode]]:
        return [MyNode]

async def comfy_entrypoint() -> MyExtension:
    return MyExtension()
```

### 10.4 V3 Type System

**Basic types:** `io.Int`, `io.Float`, `io.String`, `io.Boolean`, `io.Combo`
**ComfyUI types:** `io.Image`, `io.Mask`, `io.Latent`, `io.Conditioning`, `io.Model`, `io.VAE`, `io.CLIP`
**Advanced:** `io.Custom()`, `io.MultiType`, `io.MatchType`, `io.Autogrow`, `io.DynamicCombo`

### 10.5 V3 UI Helpers

V3 includes built-in UI helpers in `comfy_api.latest.ui`:

- `PreviewImage`, `PreviewMask`, `PreviewAudio`, `PreviewText`, `PreviewUI3D`
- `ImageSaveHelper.get_save_images_ui()`, `.get_save_animated_png_ui()`, `.get_save_animated_webp_ui()`
- `AudioSaveHelper.get_save_audio_ui()`

### 10.6 V3 Schema Fields

| Field | Purpose |
|-------|---------|
| `node_id` | Globally unique identifier (should include prefix for custom nodes) |
| `display_name` | UI label (defaults to `node_id`) |
| `category` | Menu classification string |
| `inputs` / `outputs` | Lists of type objects |
| `hidden` | Access to execution context (`io.Hidden.unique_id`, `.prompt`, `.extra_pnginfo`, `.dynprompt`, `.auth_token_comfy_org`, `.api_key_comfy_org`) |
| `is_output_node` | Triggers UI play button |
| `is_input_list` | Converts single inputs to lists |
| `enable_expand` | Allows node expansion in UI |
| `accept_all_inputs` | Passes all prompt kwargs regardless of schema |
| `is_deprecated` | Visual deprecation indicator |
| `is_experimental` | Visual experimental indicator |

### 10.7 V1 Patterns to Avoid for Easier V3 Migration

1. **Don't store state in `__init__`** -- V3 ignores instance state entirely ("Node objects do not expose 'state'" and "the node class is sanitized before execution")
2. **Don't use custom execution method names** -- V3 mandates `execute`
3. **Don't rely on instance variables (`self`)** -- V3 uses classmethods exclusively
4. **Keep node logic separate from V1 boilerplate** -- makes migration mechanical
5. **Don't use `IS_CHANGED` with boolean semantics** -- V3 renames to `fingerprint_inputs` with clearer semantics

**Recommended V1 approach for future migration:**

```python
class MyNode:
    FUNCTION = "execute"  # Already matches V3 convention

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        # Use fingerprint semantics: return unique value per unique input state
        return hash(frozenset(kwargs.items()))

    def execute(self, **kwargs):
        # Keep core logic in a separate function, not tied to self
        return _do_work(**kwargs)
```

**Source:** [V3 Migration - ComfyUI Docs](https://docs.comfy.org/custom-nodes/v3_migration), [ComfyUI#8580](https://github.com/comfyanonymous/ComfyUI/issues/8580), accessed 2026-02-22

---

## 11. Ecosystem Patterns

### 11.1 Naming Conventions

#### NODE_CLASS_MAPPINGS Keys

- Must be globally unique across all installed node packs
- Best practice: prefix with your pack name or author name
- Example: `"LLMBikeshed_TextGenerate"` rather than `"TextGenerate"`
- Avoid generic names that will collide with other packs

#### CATEGORY Organization

- Use a top-level category for your pack: `"LLM Bikeshed"`
- Use `/` for subcategories: `"LLM Bikeshed/Generation"`, `"LLM Bikeshed/Config"`
- Keep the menu structure shallow (2-3 levels max)

#### Display Names

- Use human-readable names in `NODE_DISPLAY_NAME_MAPPINGS`
- Convention varies: "Pack Prefix - Node Name" or just descriptive names
- Example: `"LLM Text Generate"`, `"LLM Provider"`

### 11.2 Common Architectural Patterns

#### Connectivity -> Options -> Generate Decomposition (from comfyui-ollama)

```
[Provider/Connectivity Node] --> [Options Node] --> [Generate Node]
         |                             |                    |
   Backend URL                   Temperature          System Prompt
   Model selection               Max tokens           User Prompt
   API key status                Top-p, etc.          Image (optional)
         |                             |                    |
         v                             v                    v
   PROVIDER_TYPE                 OPTIONS_TYPE          STRING (result)
```

Benefits:
- Each concern is a separate, reusable node
- Options node is optional (disconnect for defaults)
- Provider can be shared across multiple generate nodes

#### Meta/Context Passthrough

A dict containing provider and options config flows through nodes, so downstream nodes inherit configuration without re-specifying:

```python
# Generate node receives meta, passes it through
RETURN_TYPES = ("STRING", "LLM_META")
RETURN_NAMES = ("text", "meta")

def execute(self, prompt, meta):
    # Use meta for provider/options config
    result = generate(prompt, meta)
    return (result, meta)  # Pass meta through for chaining
```

This enables chaining multiple generate nodes without reconnecting provider/options to each one.

#### Preset + Override Pattern (from JoyCaption)

- COMBO dropdown provides preset system prompt templates
- STRING multiline field shows the selected template
- User can edit the text freely after selecting a preset
- If preset is "Custom", the field starts empty

#### Enable/Disable Toggles per Option (from comfyui-ollama V2)

```python
# Options node where each parameter has an enable toggle
"enable_temperature": ("BOOLEAN", {"default": False}),
"temperature": ("FLOAT", {"default": 0.7, "min": 0.0, "max": 2.0}),
```

Only parameters with `enable_*` set to True are included in the options dict. This gives users explicit control over which parameters are sent to the backend.

### 11.3 Node Pack Organization

```
comfyui-my-pack/
  __init__.py             # NODE_CLASS_MAPPINGS, WEB_DIRECTORY
  nodes/
    __init__.py
    generate.py           # Generation nodes
    config.py             # Provider/options nodes
    utils.py              # Shared utilities
  web/
    js/
      extension.js        # Frontend JavaScript
    docs/
      MyNodeName.md       # Help pages per node
  config.example.yaml     # Example configuration
  pyproject.toml          # Registry metadata
  requirements.txt        # Dependencies (Manager compatibility)
  README.md
  LICENSE
```

### 11.4 How Popular Packs Handle Versioning

When node packs evolve (V1 -> V2 nodes), the common pattern is:

- Keep old nodes available for backward compatibility
- Add new nodes with V2 suffix: `"OllamaGenerateV2"`
- Mark old nodes with `DEPRECATED = True` (shows visual indicator in UI)
- Document migration path

The `DEPRECATED` and `EXPERIMENTAL` class attributes control visual indicators on nodes in the UI.

### 11.5 Client-Server Compatibility

Four node implementation patterns exist in ComfyUI:

| Pattern | Description | API Compatible |
|---------|-------------|----------------|
| Server-side only | Most common. Python class, no JS. | Yes |
| Client-side only | UI modifications, no backend logic. | N/A |
| Independent Client and Server | Separate features, Comfy data flow. | Yes |
| Connected Client and Server | Direct UI-server interaction. | **No** |

**Critical:** "Any node that requires Client-Server communication will not be compatible with use through the API." If API compatibility matters, avoid patterns where the frontend JS and backend Python must communicate during execution. Pre-execution communication (like fetching model lists during node creation) is fine.

**Source:** [Overview - ComfyUI Docs](https://docs.comfy.org/custom-nodes/overview), [comfyui-ollama GitHub](https://github.com/stavsap/comfyui-ollama), [ComfyUI Discussion #2635](https://github.com/Comfy-Org/ComfyUI/discussions/2635), accessed 2026-02-22

---

## 12. Flags & Open Questions

### 12.1 Documentation Gaps

| Topic | Gap |
|-------|-----|
| Async FUNCTION methods | Official docs do not specify whether node FUNCTION methods can be async. Community evidence suggests recent ComfyUI versions execute them in an async context, but this is undocumented. Critical for aiohttp usage. |
| UI return dict format | The `{"ui": {...}, "result": (...)}` return pattern is used by built-in nodes but not formally documented. V3's `io.NodeOutput` with `ui` parameter is the documented replacement. |
| `addCustomWidget()` | Full widget `draw()`/`mouse()` interface is not in official docs. Must be learned from source code or exemplary repos (rgthree, pythongosssss). |
| `addDOMWidget()` | No official documentation or examples. |
| Widget hiding patterns | No official documentation on `"HIDDEN"` widget type or programmatic hiding. |
| `convertWidgetToInput()` | Detailed behavior and edge cases undocumented. |
| Exception handling details | Exact behavior of `handle_execution_error`, what gets cleaned up, thread safety -- all undocumented. |
| `display` parameter | Whether INT/FLOAT support a `"display": "slider"` option is referenced in some code but not formally documented. |
| `comfy.utils.ProgressBar` | Works but minimal documentation. Found in `comfy_execution/progress.py`. |

### 12.2 Contradictions Between Sources

| Topic | Contradiction |
|-------|--------------|
| MASK shape | Docs say `[H,W]` or `[B,C,H,W]`. Community commonly uses `[B,H,W]`. No single definitive standard. |
| WEB_DIRECTORY | Scaffold tool generates `"./web/js"`, but `"./web"` and `"./js"` are also common and working. All valid. |
| `widgets_values` and `forceInput`/`defaultInput` | [ComfyUI#9017](https://github.com/Comfy-Org/ComfyUI/issues/9017) reports that inputs with `defaultInput`/`forceInput` can break `widgets_values` indexing when toggled. The exact serialization behavior is version-sensitive. |

### 12.3 Version-Sensitive Behavior

| Feature | Sensitivity |
|---------|-------------|
| V3 API | Under active development. `comfy_api.latest` (`v0_0_2`) may change without warning. |
| Execution model | Changed from recursive to topological sort in PR #2666. Code relying on execution order may break. |
| `asyncio.run()` in nodes | Started failing when execution model moved to async context. Older node packs that used `asyncio.run()` broke silently. |
| `publish-node-action` | Migrated from `@main` to `@v1` in 2025. Use `@v1` for stability. |
| Cache strategies | `RAM_PRESSURE` and `LRU` are newer additions. Default is still `Classic`. |

### 12.4 Undocumented but Working Behavior

| Pattern | Status |
|---------|--------|
| `PromptServer.instance.send_sync()` | Works and is used by official walkthrough examples, but full API surface (available message types, binary data, targeting specific clients) is not documented. |
| `comfy.utils.ProgressBar` | Works for progress reporting. Integrates with WebSocket `progress` messages. Minimal documentation. |
| Custom widget `draw()`/`mouse()` interface | Works reliably. The widget interface (`draw`, `mouse`, `computeSize`, `computeLayoutSize`, `serializeValue`) is stable but undocumented. |
| `SEARCH_ALIASES` | Listed in docs but behavior details are minimal. Appears to add alternative names to the node search. |
| `DESCRIPTION` | Listed in docs but rendering behavior unclear. May show in help/info panels. |
| `DEPRECATED`, `EXPERIMENTAL` | Class attributes that add visual indicators to nodes in the UI. Briefly mentioned but not fully documented. |

---

## Node Expansion (Advanced)

Node expansion allows a node to return a subgraph that replaces itself during execution. This enables dynamic graph construction, loops, and composition patterns.

```python
def execute(self, checkpoint_path1, checkpoint_path2, ratio):
    from comfy_execution.graph_utils import GraphBuilder
    graph = GraphBuilder()

    ckpt1 = graph.node("CheckpointLoaderSimple",
                       checkpoint_path=checkpoint_path1)
    ckpt2 = graph.node("CheckpointLoaderSimple",
                       checkpoint_path=checkpoint_path2)
    merge = graph.node("ModelMergeSimple",
                       model1=ckpt1.out(0),
                       model2=ckpt2.out(0),
                       ratio=ratio)

    return {
        "result": (merge.out(0), ckpt1.out(2)),
        "expand": graph.finalize(),
    }
```

Each subnode caches independently. `GraphBuilder` handles unique ID generation. This is an advanced feature not needed for most node packs.

**Source:** [Node Expansion - ComfyUI Docs](https://docs.comfy.org/custom-nodes/backend/expansion), accessed 2026-02-22

---

## Complete V1 Node Template

For reference, a complete V1 node class with all commonly-used properties:

```python
class MyNode:
    """Node description shown in help."""

    # === Required Properties ===

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "text": ("STRING", {
                    "default": "",
                    "multiline": True,
                    "placeholder": "Enter text...",
                    "tooltip": "The input text to process",
                }),
                "mode": (["option_a", "option_b"],),
            },
            "optional": {
                "config": ("MY_CONFIG", {"forceInput": True}),
                "temperature": ("FLOAT", {
                    "default": 0.7,
                    "min": 0.0,
                    "max": 2.0,
                    "step": 0.01,
                    "tooltip": "Sampling temperature",
                }),
            },
            "hidden": {
                "unique_id": "UNIQUE_ID",
            },
        }

    RETURN_TYPES = ("STRING", "BOOLEAN")
    RETURN_NAMES = ("result", "success")
    FUNCTION = "execute"
    CATEGORY = "MyPack/Generation"

    # === Optional Properties ===

    OUTPUT_NODE = False
    # DEPRECATED = False
    # EXPERIMENTAL = False
    # SEARCH_ALIASES = ["my alias", "another name"]
    # DESCRIPTION = "Detailed description of what this node does"
    # OUTPUT_IS_LIST = (False, False)
    # INPUT_IS_LIST = False

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        # Return float("NaN") to always re-execute
        # Or return a hash for efficient caching
        return float("NaN")

    @classmethod
    def VALIDATE_INPUTS(cls, input_types=None, **kwargs):
        # Return True or error string
        return True

    def execute(self, text, mode, unique_id, config=None, temperature=0.7):
        try:
            result = process(text, mode, config, temperature)
            return (result, True)
        except Exception as e:
            # Graceful error: return error string instead of raising
            return (f"Error: {str(e)}", False)
```

---

## Sources

### Official Documentation
- [ComfyUI Docs - Overview](https://docs.comfy.org/custom-nodes/overview) -- accessed 2026-02-22
- [ComfyUI Docs - Getting Started/Walkthrough](https://docs.comfy.org/custom-nodes/walkthrough) -- accessed 2026-02-22
- [ComfyUI Docs - Properties](https://docs.comfy.org/custom-nodes/backend/server_overview) -- accessed 2026-02-22
- [ComfyUI Docs - Hidden and Flexible Inputs](https://docs.comfy.org/custom-nodes/backend/more_on_inputs) -- accessed 2026-02-22
- [ComfyUI Docs - Datatypes](https://docs.comfy.org/custom-nodes/backend/datatypes) -- accessed 2026-02-22
- [ComfyUI Docs - Tensors](https://docs.comfy.org/custom-nodes/backend/tensors) -- accessed 2026-02-22
- [ComfyUI Docs - Lifecycle](https://docs.comfy.org/custom-nodes/backend/lifecycle) -- accessed 2026-02-22
- [ComfyUI Docs - Lazy Evaluation](https://docs.comfy.org/custom-nodes/backend/lazy_evaluation) -- accessed 2026-02-22
- [ComfyUI Docs - Node Expansion](https://docs.comfy.org/custom-nodes/backend/expansion) -- accessed 2026-02-22
- [ComfyUI Docs - Data Lists](https://docs.comfy.org/custom-nodes/backend/lists) -- accessed 2026-02-22
- [ComfyUI Docs - JavaScript Hooks](https://docs.comfy.org/custom-nodes/js/javascript_hooks) -- accessed 2026-02-22
- [ComfyUI Docs - JavaScript Objects and Hijacking](https://docs.comfy.org/custom-nodes/js/javascript_objects_and_hijacking) -- accessed 2026-02-22
- [ComfyUI Docs - Help Page](https://docs.comfy.org/custom-nodes/help_page) -- accessed 2026-02-22
- [ComfyUI Docs - Publishing to Manager](https://docs.comfy.org/custom-nodes/backend/manager) -- accessed 2026-02-22
- [ComfyUI Docs - Registry Specifications](https://docs.comfy.org/registry/specifications) -- accessed 2026-02-22
- [ComfyUI Docs - V3 Migration](https://docs.comfy.org/custom-nodes/v3_migration) -- accessed 2026-02-22
- [ComfyUI Docs - Routes](https://docs.comfy.org/development/comfyui-server/comms_routes) -- accessed 2026-02-22
- [ComfyUI Docs - Execution Model Inversion Guide](https://docs.comfy.org/development/comfyui-server/execution_model_inversion_guide) -- accessed 2026-02-22
- [ComfyUI Docs - Workflow JSON Spec](https://docs.comfy.org/specs/workflow_json) -- accessed 2026-02-22
- [ComfyUI Docs - Core Concepts: Nodes](https://docs.comfy.org/development/core-concepts/nodes) -- accessed 2026-02-22
- [ComfyUI Docs - Core Concepts: Links](https://docs.comfy.org/development/core-concepts/links) -- accessed 2026-02-22
- [ComfyUI Docs - Core Concepts: Dependencies](https://docs.comfy.org/development/core-concepts/dependencies) -- accessed 2026-02-22

### GitHub
- [Comfy-Org/ComfyUI](https://github.com/Comfy-Org/ComfyUI) -- source code reference
- [Comfy-Org/publish-node-action](https://github.com/Comfy-Org/publish-node-action) -- accessed 2026-02-22
- [ComfyUI Discussion #3643 - Exception Handling](https://github.com/comfyanonymous/ComfyUI/discussions/3643) -- accessed 2026-02-22
- [ComfyUI#9007 - asyncio.run() Issue](https://github.com/Comfy-Org/ComfyUI/issues/9007) -- accessed 2026-02-22
- [ComfyUI#9017 - forceInput Serialization](https://github.com/Comfy-Org/ComfyUI/issues/9017) -- accessed 2026-02-22
- [ComfyUI#4962 - IS_CHANGED/Caching](https://github.com/comfyanonymous/ComfyUI/issues/4962) -- accessed 2026-02-22
- [ComfyUI#8580 - V3 Schema](https://github.com/comfyanonymous/ComfyUI/issues/8580) -- accessed 2026-02-22
- [ComfyUI PR #2666 - Execution Model Inversion](https://github.com/comfyanonymous/ComfyUI/pull/2666) -- accessed 2026-02-22
- [ComfyUI#1936 - Progress Bar](https://github.com/comfyanonymous/ComfyUI/issues/1936) -- accessed 2026-02-22
- [ComfyUI#9962 - Async Node Execution](https://github.com/comfyanonymous/ComfyUI/issues/9962) -- accessed 2026-02-22
- [ComfyUI#11048 - Execution Error Behavior](https://github.com/Comfy-Org/ComfyUI/issues/11048) -- accessed 2026-02-22

### Community / Secondary Sources
- [comfyui-ollama (stavsap)](https://github.com/stavsap/comfyui-ollama) -- architectural patterns reference
- [comfyui-llm-toolkit (comfy-deploy)](https://github.com/comfy-deploy/comfyui-llm-toolkit) -- provider dispatch patterns
- [ComfyUI Security Guide (Apatero, 2025)](https://apatero.com/blog/comfyui-custom-nodes-security-guide-protect-yourself-2025) -- accessed 2026-02-22
- [ComfyUI Discussion #2635 - Naming Conventions](https://github.com/Comfy-Org/ComfyUI/discussions/2635) -- accessed 2026-02-22
- [DeepWiki - ComfyUI Server and Execution Engine](https://deepwiki.com/comfyanonymous/ComfyUI/2.2-server-and-execution-engine) -- accessed 2026-02-22
- [DeepWiki - ComfyUI Caching System](https://deepwiki.com/comfyanonymous/ComfyUI/2.4-attention-mechanisms) -- accessed 2026-02-22
- [comfyui-node-standards.md (cx-sliders project memory)](C:/Users/Vir/.claude/projects/D--ai-comfyui-cx-sliders/memory/comfyui-node-standards.md) -- verified 2026-02-21, widget system, rendering pipeline, anti-patterns
