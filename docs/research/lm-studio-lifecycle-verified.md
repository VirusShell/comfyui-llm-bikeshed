# LM Studio lifecycle-related API — verified from upstream

**Date:** 2026-06-07  
**Scope:** HTTP routes used by this pack for LM Studio model memory (TTL, explicit load/unload, loaded-state check). Sources are **LM Studio official docs** and REST API reference, not third-party wikis.

## Sources

| Topic | URL | Access date | Verified how |
|-------|-----|-------------|--------------|
| Idle TTL in request payload | https://lmstudio.ai/docs/developer/core/ttl-and-auto-evict | 2026-06-07 | docs read |
| Chat completions (OAI-compat) | https://lmstudio.ai/docs/developer/openai-compat/chat-completions | 2026-06-07 | docs read |
| List models (REST) | https://lmstudio.ai/docs/developer/rest/list | 2026-06-07 | docs read |
| Load model (REST) | https://lmstudio.ai/docs/developer/rest/load | 2026-06-07 | docs read |
| Unload model (REST) | https://lmstudio.ai/docs/developer/rest/unload | 2026-06-07 | docs read |
| Upstream doc source (list) | https://github.com/lmstudio-ai/docs/blob/main/1_developer/2_rest/list.md | 2026-06-07 | code read (repo) |

## Confirmed behavior

### `ttl` in chat completions payload

Per-request idle TTL is set via top-level `ttl` (seconds) in the request body. Works for both OpenAI-compat (`POST /v1/chat/completions`) and native REST chat paths. Timer **resets on each request** to the same loaded instance. App default when omitted: **60 minutes** (3600 s), not the lifecycle node's 30 s default.

**This pack:** `LLM Lifecycle: LM Studio` → `provider["lifecycle"]["ttl"]` → adapter adds `ttl` to generate payload. Mid-chain (`skip_unload=True`): adapter sends `max(ttl * 10, 300)` to extend idle window while deferring explicit unload.

### `GET /api/v1/models` (REST — lifecycle check)

Response shape uses top-level **`models`** array (not OpenAI `data`). Each entry has:

- `key` — model identifier (matches chat `model` field)
- `loaded_instances[]` — empty when not loaded; each instance has `id` and `config` (includes `context_length` when loaded)

**This pack:** `_ensure_model_loaded_lm_studio` and `_resolve_lm_studio_instance_id` parse `models[].key` + `loaded_instances`. OpenAI-shaped `data[].id` accepted as fallback for tests only.

### `POST /api/v1/models/load`

Body: `model` (required), optional `context_length`, optional `echo_load_config`. Returns `instance_id`, `load_config.context_length`, etc.

**This pack:** Called when model not loaded or loaded with wrong `context_length`. Uses `_safe_post` (interruptible).

### `POST /api/v1/models/unload`

Body: `instance_id` (required) — from `loaded_instances[].id`, not always equal to model `key` when multiple instances exist.

**This pack:** `_unload_model_lm_studio` resolves `instance_id` via GET when possible, falls back to model name. Uses **bare `requests.post`** (not interruptible) — intentional post-success cleanup; same as Textgen unload. See [`cancel-interrupt-status.md`](cancel-interrupt-status.md).

### JIT loading + Auto-Evict

JIT loads on first request; Auto-Evict (default ON) unloads prior JIT-loaded model when a new one loads. Complements per-request TTL and this pack's explicit unload on last chain node.

## Partially confirmed / operational

### Client disconnect during non-streaming chat

No explicit "stop generation" API wired for LM Studio (unlike Textgen `stop-generation`). Client abort via interrupt polling may or may not stop GPU work — **[VERIFY] empirical** on live LM Studio.

### `context_length` via explicit load vs JIT

Explicit `POST /api/v1/models/load` with `context_length` is required for reliable ctx settings when JIT would ignore desired ctx (tracker cites LM Studio issue #1463 — **[VERIFY]** issue still open/applicable at user's LM Studio version).

## Unknown / version-sensitive

- Exact behavior when `instance_id` in unload does not match any loaded instance (silent no-op vs error).
- Whether `GET /api/v1/models` response ever used OpenAI `data[]` shape in older LM Studio builds.
- Host inference stop on ComfyUI Cancel for `stream: false` chat.

## Audit vs this repository (2026-06-07)

| Area | Status |
|------|--------|
| `adapters/oai_compat.py` `_ensure_model_loaded_lm_studio` | **Fixed:** was parsing `data[].id`; now uses REST `models[].key` per upstream list API. |
| `adapters/oai_compat.py` `_unload_model_lm_studio` | **Fixed:** resolves `loaded_instances[].id` before unload; documents non-interruptible bare POST. |
| `nodes/lifecycle.py` | **Verified:** outputs `{type, ttl, context_length}` matching adapter expectations. |
| TTL default 30 s (lifecycle node) vs LM Studio app default 60 min | **By design** — pack default favors VRAM reclamation; user-tunable. |

**2026-06-08 code re-read:** No drift — `_iter_lm_studio_model_entries`, `_ensure_model_loaded_lm_studio`, `_unload_model_lm_studio` still match this note. Live cancel QA **[VERIFY]** remains open (`cancel-interrupt-status.md`).

## Applies to

- `adapters/oai_compat.py` — LM Studio lifecycle paths
- `nodes/lifecycle.py` — `LLMLifecycleLMStudio`
- Tracker rows A-15, A-18, A-22
- [`cancel-interrupt-status.md`](cancel-interrupt-status.md) — LM Studio cancel limits
