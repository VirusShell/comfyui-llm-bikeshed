# Backend API Parameters Reference

> **Last updated:** 2026-06-08  
> **Status:** Reference for **in-pack** backends (LM Studio, Textgen, OpenAI). Ollama native API section retained for cross-backend mapping history only — **Ollama removed from pack (D-3, v0.3.0).**  
> **Resolution tracker:** API-4, API-7 (Textgen auth). Allowlists in code: `adapters/oai_compat.py` `BACKEND_ALLOWLISTS`.

## Ollama Native API (historical — pack removed D-3)

**Endpoint:** `POST {url}/api/chat`

### Request Structure

Top-level fields: `model` (required), `messages` (required), `stream`, `format`, `keep_alive`, `tools`, `think`

Parameters go in the `options` object (NOT top-level):

### Sampling Parameters

| Parameter | Type | Default | Notes |
|-----------|------|---------|-------|
| `temperature` | float | 0.8 | |
| `top_k` | int | 40 | |
| `top_p` | float | 0.9 | |
| `min_p` | float | 0.0 | |
| `seed` | int | 0 | |
| `typical_p` | float | 1.0 | Typical sampling |

### Generation Parameters

| Parameter | Type | Default | Notes |
|-----------|------|---------|-------|
| `num_predict` | int | -1 | Max tokens. -1 = unlimited |
| `num_ctx` | int | 2048 | Context window size |
| `stop` | string/list | -- | Stop sequences |

### Repetition Parameters

| Parameter | Type | Default | Notes |
|-----------|------|---------|-------|
| `repeat_penalty` | float | 1.0 | |
| `repeat_last_n` | int | 64 | |
| `presence_penalty` | float | 0.0 | |
| `frequency_penalty` | float | 0.0 | |
| `penalize_newline` | bool | -- | |

### Mirostat Parameters (Ollama-Only)

| Parameter | Type | Default | Notes |
|-----------|------|---------|-------|
| `mirostat` | int | 0 | 0=off, 1=v1, 2=v2 |
| `mirostat_eta` | float | 0.1 | |
| `mirostat_tau` | float | 5.0 | |

### Other

| Parameter | Type | Default | Notes |
|-----------|------|---------|-------|
| `tfs_z` | float | 1.0 | Tail-free sampling |
| `num_keep` | int | -- | Context tokens to keep |
| `num_batch` | int | -- | Batch size |
| `num_gpu` | int | -- | GPU layers |
| `num_thread` | int | -- | CPU threads |

### Unknown Parameter Handling

`options` field typed as `map[string]interface{}` with `additionalProperties: true`. **Unknown keys are silently ignored.** Safe to send extra params.

### Model Memory

`keep_alive` (top-level, not in `options`): string or number. Examples: `"30s"`, `"5m"`, `0` (unload immediately). Timer resets on each request.

---

## LM Studio (OpenAI-Compatible)

**Endpoint:** `POST {url}/v1/chat/completions`
**Model list:** `GET {url}/v1/models`

### Standard OAI Parameters

`model`, `messages`, `temperature`, `top_p`, `max_tokens`, `stream`, `stop`, `presence_penalty`, `frequency_penalty`, `logit_bias`, `seed`

### LM Studio Extensions

| Parameter | Type | Default | Notes |
|-----------|------|---------|-------|
| `top_k` | int | -- | |
| `repeat_penalty` | float | -- | |
| `ttl` | int (seconds) | 3600 | Model idle timeout (app default is 60 min) |
| `draft_model` | string | -- | Speculative decoding |

### Model Memory

- **JIT loading:** Models load automatically on first request
- **TTL:** Per-request, resets on each request. Default 60 minutes (not 30s as originally assumed)
- **Auto-Evict:** Enabled by default. Loading new JIT model unloads previous

### Unknown Parameter Handling

Not explicitly documented. Likely ignores unknown top-level params (llama.cpp backend). **Needs empirical testing.**

---

## text-generation-webui (OpenAI-Compatible)

**Endpoint:** `POST {url}/v1/chat/completions`

### Standard OAI Parameters

`model`, `messages`, `temperature`, `top_p`, `max_tokens`, `stream`, `stop`, `presence_penalty`, `frequency_penalty`, `logit_bias`, `n`

### text-gen-webui Extensions

| Parameter | Type | Default | Notes |
|-----------|------|---------|-------|
| `top_k` | int | -- | |
| `typical_p` | float | 1.0 | |
| `min_p` | float | -- | |
| `repeat_penalty` | float | -- | |
| `seed` | int | -- | |
| `preset` | string | -- | Server-side preset name |
| `sampler_priority` | list[str] | -- | Custom sampler order |
| `mode` | string | "instruct" | instruct/chat/chat-instruct |
| `instruction_template` | string | -- | |
| `continue_` | bool | False | Continue previous generation |
| `dynamic_temperature` | bool | -- | |
| `tfs` | float | -- | Tail-free sampling |
| `top_a` | float | -- | Top-A sampling |

### Model Management Endpoints (auth split — see API-6)

| Endpoint | Method | Auth gate | Purpose |
|----------|--------|-----------|---------|
| `/v1/internal/model/info` | GET | API key (`check_key`) | Current loaded model info |
| `/v1/internal/model/list` | GET | Admin key (`check_admin_key`) | List available models |
| `/v1/internal/model/load` | POST | Admin key | Load model (`{"model_name": "...", "args": {...}}`) |
| `/v1/internal/model/unload` | POST | Admin key | Unload current model |
| `/v1/internal/stop-generation` | POST | API key | Stop in-flight generation (cancel) |

Upstream: [`textgen-lifecycle-verified.md`](../research/textgen-lifecycle-verified.md).

### Admin Key Handling (API-7)

- `--api-key KEY` protects chat, `model/info`, and `stop-generation` when set.
- `--admin-key ADMIN_KEY` protects list/load/unload when set.
- At **server startup**, if only `--api-key` is set, Textgen copies it to `admin_key` — admin routes then accept the same bearer (`run_server()` in `modules/api/script.py`).
- When **both** flags are set to **different** values, clients must send the matching bearer per route (no per-request fallback).
- **Pack config:** support both `api_key` and `admin_key`; when user configures only one, pack helpers may mirror for convenience — see `get_textgen_auth_keys()`.

### Unknown Parameter Handling

Pydantic model likely rejects unknown top-level fields. **Needs empirical testing.** The `GenerationOptions` class is extensive enough to cover most use cases.

---

## Cross-Backend Parameter Mapping

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
| TFS | `options.tfs_z` | -- | `tfs` |
| Typical P | `options.typical_p` | -- | `typical_p` |
| Model keep-alive | `keep_alive` (top-level) | `ttl` (top-level) | explicit unload endpoint |

## Sources

- [LM Studio Chat Completions](https://lmstudio.ai/docs/developer/openai-compat/chat-completions)
- [LM Studio TTL and Auto-Evict](https://lmstudio.ai/docs/developer/core/ttl-and-auto-evict)
- [LM Studio REST list/load/unload](https://lmstudio.ai/docs/developer/rest/list)
- [Textgen OpenAI API module](https://github.com/oobabooga/textgen/blob/main/modules/api/script.py) — routes and auth (authoritative; wiki mirrors non-authoritative)
- [Textgen typing.py](https://github.com/oobabooga/textgen/blob/main/modules/api/typing.py)
- Ollama docs (historical cross-map only): [Ollama /api/chat](https://docs.ollama.com/api/chat)
