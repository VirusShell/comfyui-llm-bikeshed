# Design Review Update — 2026-03-10

## Purpose

This document contains corrections, additions, and clarifications from the final design review. It is self-contained — all information needed to act on it is included here. Where this document conflicts with prior docs, this document wins.

---

## 1. New Requirement: text-gen-webui Model Loading Before Generation

### Problem

text-gen-webui does NOT auto-load models on chat/completions requests like Ollama and LM Studio do. If no model is loaded (or if the model was previously unloaded by our adapter), the generation request will fail.

| Backend | Load Behavior | Unload Behavior |
|---------|--------------|-----------------|
| Ollama | Automatic on request | Timer (`keep_alive`) |
| LM Studio | JIT on first request | Timer (`ttl`) |
| text-gen-webui | **Manual only** — must call load endpoint | **Manual only** — must call unload endpoint |

### Required Lifecycle

The text-gen-webui adapter must handle the full model lifecycle:

1. **Before generation:** Call `GET {url}/v1/internal/model/info` to check if the correct model is loaded
2. **If wrong model or no model:** Call `POST {url}/v1/internal/model/load` with `{"model_name": "selected_model"}`
3. **Generate:** Call `POST {url}/v1/chat/completions` as normal
4. **After generation (last node in chain only):** Call `POST {url}/v1/internal/model/unload`

The load and unload endpoints require the admin key if one is configured on the server (via `--admin-key` or `--api-key`). If no auth is configured on the server, these endpoints are open.

### New Functional Requirement

**FR-19:** text-gen-webui adapter checks model status via `GET /v1/internal/model/info` and loads the selected model via `POST /v1/internal/model/load` before generation if the correct model is not already loaded. Uses admin key from config if available.

---

## 2. Model Selection Priority Logic

### Problem

Each Provider node has both a `model` COMBO widget (populated by JS from the backend) and a `model_fallback` STRING input (`defaultInput: True` for manual entry). No rule exists for which one the adapter uses.

### Rule

**STRING fallback overrides COMBO.** If `model_fallback` has a non-empty value (user typed something or connected a STRING to it), use that. Otherwise use the COMBO dropdown value.

The COMBO is the convenience (auto-populated, easy selection). The STRING is the override (offline fallback, connection from another node, advanced use).

### Update Needed

Add this priority rule to the acceptance criteria for each Provider node (US-1 AC-1.x, US-2 AC-2.x, US-3 AC-3.x). Example AC wording: "If `model_fallback` input has a non-empty value, it overrides the COMBO dropdown selection for model name."

---

## 3. Options Node Architecture — Ollama Core/Extra Split

### Problem

The Ollama Options node has 17 parameters. With toggle+value pairs, that's 34 widgets — the exact anti-pattern identified in comfyui-ollama's OllamaOptions node (extremely tall, visually overwhelming).

### Solution

Split into two nodes:

**Ollama Options (Core)** — the most commonly adjusted parameters. NO toggles. Uses sentinel values instead: each param has a default that means "use model default." If the value equals the sentinel, the adapter excludes it from the request.

Parameters:
- `temperature` (FLOAT, default -1 → model default, typical range 0.0–2.0)
- `top_k` (INT, default -1 → model default)
- `top_p` (FLOAT, default -1 → model default)
- `seed` (INT, default -1 → random)
- `num_predict` (INT, default -1 → unlimited, maps to max_tokens concept)
- `num_ctx` (INT, default -1 → model default of 2048)
- `stop` (STRING, default empty → no stop sequences)

This is 7 value widgets. Compact, clean, no toggles needed.

The sentinel pattern: adapter builds the options dict, checks each value against its sentinel, and only includes params where the user set a non-sentinel value. For example:
```python
if temperature != -1:
    options["temperature"] = temperature
# if temperature == -1, it's excluded entirely → model uses its own default
```

**Ollama Options (Extra)** — advanced tuning knobs. Uses BOOLEAN toggle per parameter (`label_on`: "ON", `label_off`: "OFF"). Toggle OFF = excluded from request (model default). Toggle ON = value sent.

Parameters:
- `mirostat` (INT COMBO: 0/1/2)
- `mirostat_eta` (FLOAT, default 0.1)
- `mirostat_tau` (FLOAT, default 5.0)
- `repeat_penalty` (FLOAT, default 1.1)
- `repeat_last_n` (INT, default 64)
- `frequency_penalty` (FLOAT, default 0.0)
- `presence_penalty` (FLOAT, default 0.0)
- `tfs_z` (FLOAT, default 1.0)
- `typical_p` (FLOAT, default 1.0)
- `min_p` (FLOAT, default 0.0)

10 parameters × (toggle + value) = 20 widgets. Still tall but these are explicitly advanced controls that most users won't touch.

**Chaining:** Ollama Extra Options has an `options_in` (LLM_OPTIONS) input and outputs LLM_OPTIONS. Ollama Core Options also has an `options_in` (LLM_OPTIONS) input and outputs LLM_OPTIONS. The chain is:

```
[Ollama Extra Options] → options_in → [Ollama Core Options] → options → [Generation Node]
```

Or just:

```
[Ollama Core Options] → options → [Generation Node]
```

The Extra node is entirely optional. The generation node still has a single `options` input — it doesn't know or care whether Core alone or Core+Extra produced the options dict. The merge is simple: downstream values override upstream for any key collision (Core wins over Extra for overlapping keys, though in practice there shouldn't be overlap since they have different parameter sets).

### LM Studio and text-gen-webui

**LM Studio** has 9 parameters. A single node with toggles is 18 widgets — borderline but probably acceptable. Don't split unless it looks bad in the UI during implementation.

LM Studio Options parameters: temperature, top_p, max_tokens, seed, stop, top_k, repeat_penalty, presence_penalty, frequency_penalty.

**text-gen-webui** has 12 parameters. A single node with toggles is 24 widgets — likely too tall. If it looks bad, split along the same pattern:

text-gen-webui Core: temperature, top_p, max_tokens, seed, stop, top_k (sentinel values, no toggles)
text-gen-webui Extra: min_p, repeat_penalty, presence_penalty, frequency_penalty, typical_p, tfs (toggles)

But **don't split preemptively** — implement as a single node first, evaluate the height in the actual UI, and split only if it's a problem. The Ollama split is committed because 17 params is definitively too many.

### Update to FR-4 and Related ACs

FR-4 changes from "Three per-provider Options nodes with BOOLEAN toggles" to "Per-provider Options nodes. Ollama uses Core/Extra split (Core: sentinel values, Extra: toggles). LM Studio and text-gen-webui use single node with toggles (may split later if too tall)."

Update AC-8.x (Ollama Options) to reflect two nodes. Add new ACs for the Extra node. Update AC-8.1 to say "Ollama Core Options node exists with sentinel-value pattern (no toggles)."

---

## 4. Built-in Load Text File Node

### Problem

The design assumes users have comfyui-custom-scripts or similar installed for loading system prompts from files. Some users won't have it, won't want to install another pack, or may not know how. The project should be self-contained.

### Solution

Add a **Load Text File** utility node to the node pack. This is separate from the Preset Loader.

**Load Text File node:**
- COMBO widget listing `.txt` files from a directory (default: ComfyUI's `input/` folder)
- Output: STRING containing the file's text content
- Connect to any generation node's `system_prompt` input (or any STRING input)
- Keep it minimal: COMBO of filenames, one output. No editing, no saving, no subdirectory browsing.

**How this differs from the Preset Loader:**

| | Preset Loader | Load Text File |
|---|---|---|
| **Reads from** | `{node_pack}/presets/` directory | ComfyUI's `input/` folder (user-configurable) |
| **Purpose** | Shipped system prompt templates, curated by us | User's own text files |
| **Content ships with pack** | Yes (once authored) | No — user's files |
| **Who manages the files** | Pack developers | The user |

Both output STRING. Both connect to `system_prompt`. Having both built-in means a user installs this one pack and has everything needed for prompt loading without external dependencies.

### New Functional Requirement

**FR-20:** Load Text File utility node. COMBO widget lists `.txt` files from a configurable directory (default: ComfyUI `input/` folder). Output is STRING with file contents. Refresh picks up new files (ComfyUI's `r` hotkey triggers node refresh which re-calls `INPUT_TYPES`).

---

## 5. Model List Authentication

### Findings from Research

All three backends work **without API keys by default** for model listing:

- **Ollama:** No authentication required for local API access (`http://localhost:11434`). `GET /api/tags` works with no key out of the box.
- **LM Studio:** Authentication is disabled by default. Model list endpoints work without tokens. Auth is opt-in — user must explicitly enable it in LM Studio's Developer Settings.
- **text-gen-webui:** Auth is opt-in via `--api-key` / `--admin-key` flags at server start. If no keys are configured on the server, all endpoints (including `GET /v1/internal/model/list`) are open.

### Implementation Pattern

PromptServer model list endpoints should:
1. Attempt the request without auth headers first
2. Only include auth headers (`Authorization: Bearer {key}` or admin key) if a key is configured in config.yaml
3. If the request fails with 401/403, log an info-level message: "Backend requires authentication. Configure API key in config.yaml."
4. Return an empty model list to the frontend (not an error) so the UI degrades gracefully (COMBO shows fallback state, user can still type model name manually)

---

## 6. Unknown Parameter Handling (Empirical Testing)

The research.md already documents this but the answers need empirical confirmation during implementation:

- **Ollama:** Confirmed safe. `options` field uses `additionalProperties: true`. Unknown params are silently ignored.
- **LM Studio:** Not explicitly documented. Likely ignores unknowns (llama.cpp under the hood) but needs testing. Send a request with a made-up param like `"fake_param": 42` and observe: does it succeed, fail, or log a warning?
- **text-gen-webui:** Pydantic model may reject unknown top-level fields. Needs the same test. The allowlist approach means we only send known params, so this is a safety net — but test it anyway and log results.

These are not design blockers. The allowlist approach (only send params the backend is known to accept) handles this regardless. But confirming actual behavior removes an assumption.

---

## 7. max_tokens Default Update

The Basic generation node's `max_tokens` default is now **1024** (was 256 in the earlier draft). 256 was too short for most practical use cases. 1024 covers the user's Flux prompt optimization workflow (which uses 110-170 tokens) with plenty of room, and is reasonable for longer-form generation.

Update AC-5.1: `max_tokens` (INT, default **1024**).

The user can always override this on the node.

---

## 8. Preset Directory Separation

**`presets/`** — in node pack root. Ships with built-in system prompt templates. Gets overwritten on pack update. Users should treat these as read-only reference.

User-created presets go in ComfyUI's `input/` folder (or wherever they keep their files) and are loaded via the **Load Text File** node (section 4 above). This avoids any collision between shipped content and user content — different directories, different nodes, different purposes.

No `presets/user/` subdirectory needed. The separation is clean: Preset Loader reads `presets/`, Load Text File reads `input/`.

---

## 9. Generation Node Hidden Inputs for Graph Introspection

Both generation nodes (Basic and Advanced) need these hidden inputs declared for the unload deferral mechanism (A-15, P-10):

```python
"hidden": {
    "prompt": "PROMPT",
    "unique_id": "UNIQUE_ID"
}
```

The PROMPT hidden input provides the full execution graph as a dict keyed by node ID. The generation node's FUNCTION method uses this to reverse-index downstream connections and determine if another generation node is downstream on the meta output.

Implementation pattern:

```python
def find_downstream_gen_nodes(prompt, my_node_id, meta_output_index):
    """Check if any downstream node on meta output is a generation node."""
    gen_node_types = {"LLMBikeshed_TextGenerate", "LLMBikeshed_TextGenerateAdvanced"}
    for node_id, node_def in prompt.items():
        for input_name, input_val in node_def.get("inputs", {}).items():
            if isinstance(input_val, list) and len(input_val) == 2:
                if str(input_val[0]) == str(my_node_id) and input_val[1] == meta_output_index:
                    if node_def.get("class_type") in gen_node_types:
                        return True
    return False
```

If this returns `True`, the current node is mid-chain — skip unload / use long keep_alive. If `False`, this is the last generation node — fire unload (text-gen-webui) or use the Provider's configured short keep_alive/ttl.

---

## 10. Adapter Allowlist Filtering — Logging Level

When an adapter drops an unsupported parameter, it should log at **info level**, not debug. Users should see this in the ComfyUI console without having to enable debug logging. The message should be clear:

```
[llm-bikeshed] Parameter 'mirostat' not supported by LM Studio backend, skipping
```

This is especially important for the meta passthrough case — if a user chains generation nodes and switches providers mid-chain via explicit provider override, options tuned for one backend may not all work on the next. The info-level log makes this visible.

---

## 11. Error Handling Summary

| Situation | Mechanism | Detail |
|-----------|-----------|--------|
| API call fails (HTTP error) | Raise exception in FUNCTION | Message includes: backend name, URL, HTTP status, response body. Workflow halts, red outline on node. |
| Network timeout | Raise exception | Default 120s, configurable per-provider in config.yaml. Message identifies provider and URL. |
| Invalid config (pre-execution) | VALIDATE_INPUTS | Check URL format valid, required provider config present. Prevents execution with known-bad config. |
| Unsupported parameter dropped | Toast notification + info log | JS toast: "Parameter X not supported by Y, ignored." Console log at info level. Non-fatal, generation proceeds. |
| Backend offline (model list) | Graceful degradation | Return empty model list to frontend. COMBO shows fallback. User can type model name in STRING fallback. Log info message. |
| Auth failure (401/403) | Log + raise exception | Message: "Authentication failed for {backend}. Check API key configuration in config.yaml." |
| Model not loaded (text-gen-webui) | Adapter handles automatically | Check model status, load if needed (FR-19), then generate. Transparent to the user. |

No retry logic in v0.1.0. Fail immediately, surface errors clearly.

---

## 12. Config System

**Files:**
- `config.example.yaml` — ships with pack, documented defaults for all three backends
- `config.yaml` — user copy, gitignored

**Merge-on-load:** At runtime, `config.example.yaml` is deep-merged with `config.yaml`. User values win for any key present in both. New keys from example appear with defaults after a pack update. User-added custom keys are preserved. Neither file is modified on disk.

**Caching:** Config is cached on module load. A PromptServer endpoint `POST /llm-bikeshed/reload-config` triggers re-read without ComfyUI restart.

**API key resolution chain:** config.yaml → environment variable (`LLM_BIKESHED_{PROVIDER}_API_KEY`) → None.

**text-gen-webui dual key support:** Config supports both `api_key` (for generation endpoints) and `admin_key` (for model load/unload/list). If only one is configured, use it for both purposes. This matches text-gen-webui's own behavior where `--api-key` is used for admin ops if no separate `--admin-key` is set.

**Safety:** `yaml.safe_load()` only. Never `yaml.load()`.

---

## 13. Custom Types Reference

| Type | Contents | Produced By | Consumed By |
|------|----------|-------------|-------------|
| `LLM_PROVIDER` | Dict: backend URL, model name, adapter type, auth info, memory management settings (keep_alive/ttl/unload behavior) | Provider nodes | Generation nodes |
| `LLM_OPTIONS` | Dict: only the inference parameters the user enabled/set (sentinel-excluded or toggle-enabled) | Options nodes | Advanced Generation node |
| `LLM_META` | Dict: provider config + options, for chaining generation nodes without re-specifying config | Generation nodes (output) | Generation nodes (input) |

Custom types in ComfyUI are connection-only — they cannot render as widgets. `forceInput` is not needed for custom types.

**Meta precedence on Advanced Generation node:** If both `meta` and explicit `provider` are connected, explicit `provider` wins. If both `meta` (carrying options) and explicit `options` are connected, explicit `options` wins. Meta is a convenience for chaining, not a lock-in.

---

## 14. Frontend JS Summary

Extension name: `llm-bikeshed.model-dropdown`
Files served from: `./js` directory (WEB_DIRECTORY = "./js")

Responsibilities:
- Populate model COMBO widgets on Provider nodes from PromptServer endpoints
- `nodeCreated` hook fetches models for each Provider node type
- Refresh button per Provider node re-queries backend
- Saved model names persist in `widgets_values` across save/load regardless of backend state
- Toast notifications via `app.extensionManager.toast.add()` for non-fatal warnings (unsupported params, etc.)

PromptServer endpoints (one per backend):
- Ollama: queries `GET {url}/api/tags`
- LM Studio: queries `GET {url}/v1/models`
- text-gen-webui: queries `GET {url}/v1/internal/model/list` (with admin key if configured)

All PromptServer endpoints use `async def` handlers with `asyncio.to_thread()` to call synchronous `requests` without blocking the event loop.

---

## Summary of Changes for Requirements

| Item | Type | Description |
|------|------|-------------|
| FR-19 | New | text-gen-webui adapter pre-loads model before generation |
| FR-20 | New | Load Text File utility node (reads from `input/` folder) |
| FR-4 | Update | Ollama Options split into Core (sentinel values) + Extra (toggles). LM Studio/text-gen-webui single node with toggles (split later if too tall) |
| AC-5.1 | Update | max_tokens default changed to 1024 |
| AC-1.x/2.x/3.x | Update | Add model selection priority: STRING fallback overrides COMBO dropdown |
| PromptServer endpoints | Update | Attempt without auth first, include key only if configured, graceful 401/403 handling |
