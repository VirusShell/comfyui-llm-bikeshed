# ComfyUI LLM Bikeshed

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Tests](https://github.com/VirusShell/comfyui-llm-bikeshed/actions/workflows/test.yml/badge.svg)](https://github.com/VirusShell/comfyui-llm-bikeshed/actions/workflows/test.yml)

ComfyUI custom nodes for local LLM text generation. The intended new graph is **LLM Connection** → **LLM Generate (Advanced)**. Connection is one adaptive host (Auto or a pinned backend), a URL, a model, and one **Manage VRAM** toggle. Advanced Generate is the prompt plus an output `max_tokens` above `seed`. That cap does not need an Options node. API keys live in config or environment variables only — never in workflow JSON.

**Legacy / compatibility (still registered):** **LLM Generate (Basic)**, **LLM Options**, **LLM Provider: OAI Compatible**, **LLM Provider: Textgen**, and the **Lifecycle** nodes. Existing workflows keep working. New graphs should not start there.

**Scope:** llama.cpp is Connection (or the legacy OAI Compatible node) speaking `/v1`. There is no dedicated llama-server node. Older scope notes live in [`docs/proposals/product-direction-and-scope.md`](docs/proposals/product-direction-and-scope.md).

## Features

- **LLM Connection** (start here) — host mode (Auto or pin LM Studio / Textgen / llama.cpp / OpenAI / Generic OAI), URL + model, one **Manage VRAM** toggle for Textgen and LM Studio, secret-free status. Models via `POST /llm-bikeshed/models/connection`. Picking a model does not load weights.
- **LLM Generate (Advanced)** (intended Generate) — face `max_tokens` above `seed`. `0` omits the output cap. Optional `provider` / `options` / `meta`. No Options node on this path.
- **2 Utility nodes** — Preset Loader and Load Text File
- **VRAM** — Connection **Manage VRAM** (default ON) loads and unloads Textgen, or sets LM Studio TTL, around generation. Chain-aware unload uses `meta`. OpenAI, generic, and llama.cpp hide the toggle; chat still runs.
- **Secure** — API keys from config or environment variables, never in workflow JSON
- **Minimal dependencies** — only `pyyaml` and `requests` (no provider SDKs)
- **Legacy** — Basic Generate, Options, Provider, and Lifecycle nodes stay registered (see [Legacy / compatibility](#legacy--compatibility))

## Requirements

- ComfyUI (V1 node spec)
- Python 3.10+
- At least one LLM backend running, for example:
  - [LM Studio](https://lmstudio.ai/) (default: `http://localhost:1234`)
  - [Textgen / text-generation-webui](https://github.com/oobabooga/text-generation-webui) (default: `http://localhost:5000`) - verified HTTP/auth for internal model routes is summarized in [`docs/research/textgen-lifecycle-verified.md`](docs/research/textgen-lifecycle-verified.md). **VRAM / model memory today:** see the same doc (appendix) and the short summary under [Architecture](#architecture).
  - Optional: **OpenAI** (`https://api.openai.com`) - set `providers.openai.api_key` or `LLM_BIKESHED_OPENAI_API_KEY`; keys never stored in workflows
  - Optional: **llama.cpp** server (e.g. `llama-server`) exposing OpenAI-compatible `/v1` - use **LLM Connection** (host mode Auto or llama.cpp) or legacy **OAI Compatible** (see [Quick Start](#quick-start))

Native **Ollama** (`/api/chat`) is not supported by this pack; use a dedicated Ollama-focused custom node pack, or an OpenAI-compatible gateway if your stack exposes `/v1/chat/completions`.

## Installation

1. Clone or download this repository into your ComfyUI `custom_nodes/` directory:

   ```bash
   cd ComfyUI/custom_nodes
   git clone https://github.com/VirusShell/comfyui-llm-bikeshed.git
   ```

2. Install dependencies (same set as `pyproject.toml` `[project.dependencies]`):

   ```bash
   cd comfyui-llm-bikeshed
   pip install -r requirements.txt
   ```

   Registry / CNR installs use `pyproject.toml`; git clones should still run `pip install -r requirements.txt` so `pyyaml` and `requests` are present if your ComfyUI env does not already provide them.

3. Restart ComfyUI. Nodes appear under the **LLM Bikeshed** category.

Example workflows are in [`example_workflows/`](example_workflows/). Load them from ComfyUI's template browser or via **Load**. Start with [`connection_generate.json`](example_workflows/connection_generate.json) (**LLM Connection** → **LLM Generate (Advanced)**).

## Configuration

1. Copy the example config:

   ```bash
   cp config.example.yaml config.yaml
   ```

2. Edit `config.yaml` with your settings:

   ```yaml
   providers:
     lm_studio:
       url: "http://localhost:1234"
       timeout: 120
       # api_key: "your-api-key-here"

     openai:
       url: "https://api.openai.com"
       timeout: 120
       # api_key: "your-api-key-here"

     text_gen_webui:
       url: "http://localhost:5000"
       timeout: 120
       # api_key: "your-api-key-here"
       # admin_key: "your-admin-key-here"

     oai_compat:
       timeout: 120
       # Shared fallback for Connection + OAI Compatible + LM Studio / llama.cpp / OpenAI.
       # api_key: "your-api-key-here"
   ```

3. `config.yaml` is gitignored - your keys and overrides stay local.

   Legacy `providers.ollama` keys in an existing `config.yaml` are ignored by this pack (deep-merge preserves them; you may delete that block manually).

### API Key Resolution

Keys are resolved in this order (first match wins) per provider slot:

1. `config.yaml` provider entry (`api_key` / `admin_key`)
2. Environment variable: `LLM_BIKESHED_{PROVIDER}_API_KEY` (e.g. `LLM_BIKESHED_LM_STUDIO_API_KEY`)
3. For admin role only: `LLM_BIKESHED_{PROVIDER}_ADMIN_KEY` (see Textgen dual-key below)
4. None (many open local servers need no key)

**OAI-shaped fallback:** for `lm_studio`, `openai`, `llamacpp`, and generic OAI backends (Connection or OAI Compatible), if the backend slot is empty the pack also tries `providers.oai_compat` (same helper for Refresh Models and Generate). Textgen keeps its own merge via `get_textgen_auth_keys` (`text_gen_webui` then `oai_compat`).

**Cookbook (pick one):**

| Goal | What to set |
|------|-------------|
| OpenAI cloud | `providers.openai.api_key` or `LLM_BIKESHED_OPENAI_API_KEY` |
| LM Studio / proxy with optional auth | key under `providers.lm_studio` **or** only under `providers.oai_compat` - both Refresh Models and Generate use that key |
| llama.cpp with a key | put the key under `oai_compat`, or set `LLM_BIKESHED_LLAMACPP_API_KEY` / a hand-added `providers.llamacpp.api_key` |
| Textgen single key | set `api_key` (and optionally the same value as `admin_key`) under `text_gen_webui` **or** only under `oai_compat` |
| Textgen distinct `--api-key` / `--admin-key` | set both `providers.text_gen_webui.api_key` and `.admin_key` to match the server flags (chat/`model/info` vs list/load/unload) |

After editing `config.yaml`, **restart ComfyUI** (there is no browser set-key / reload-config endpoint).

API keys never appear in workflow JSON - Connection / Provider nodes have no key widget.

## Nodes

### LLM Connection (recommended)

Configure a backend in one node. Outputs `LLM_PROVIDER` (same type as the legacy providers).

| Setting | Role |
|---------|------|
| `url` | Base URL **without** a duplicated `/v1` suffix (e.g. `http://127.0.0.1:1234`) |
| `host_mode` | `Auto (detect)` or pin **LM Studio** / **Textgen** / **llama.cpp** / **OpenAI / OAI-compat** / **Generic OAI** |
| `model` | Catalog COMBO for Textgen / LM Studio / OpenAI; free-text for llama.cpp / generic |
| `manage_model_memory` | **Manage VRAM / Manage memory** (default ON). Textgen: load before generate / unload after chain when ON. LM Studio: TTL + context on load when ON. OFF: pack does not load, unload, or set TTL. Hidden for OpenAI, generic, and llama.cpp |
| `ttl` / `context_length` | LM Studio only, and only while Manage VRAM is ON |
| `model_fallback` | Optional STRING input - overrides dropdown when connected |
| `timeout` | Advanced; `0` = config for effective backend, then `oai_compat`, then 120 |

**Model pick does not load weights** (Vir Q6): changing the model dropdown never calls load. Weights load when Generate runs (and the face VRAM policy asks for it) or when Manage VRAM needs an explicit load. `POST /llm-bikeshed/models/ensure-loaded` remains available for those paths; it is not wired to model selection.

**Refresh Models** calls `POST /llm-bikeshed/models/connection` with `{ "url", "host_mode" }` and updates the model widget plus read-only status lines (detected / effective backend, loaded model, auth hint, VRAM policy). The VRAM line follows the toggle (`manage on` / `manage off`) or says the toggle is hidden. No separate Lifecycle node is required for new graphs.

**Migration:** Replace **Provider** (+ optional **Lifecycle**) with **LLM Connection**, and **Basic** or an Options wall with **LLM Generate (Advanced)**. Wire Connection `provider` into Advanced `provider`.

### LLM Generate (Advanced) (intended)

The Generate node for new graphs. Outputs `text` (STRING) and `meta` (LLM_META).

| Input | Role |
|-------|------|
| `system_prompt` / `prompt` | Chat messages. Empty system text is omitted. |
| `max_tokens` | Output cap only (not prompt + completion). Sits **above** `seed`. Default 1024. Min 0, max 128000. |
| `seed` | Always sent, including `0`. |
| `provider` | Optional socket. Connect **LLM Connection** here. |
| `options` / `meta` | Optional. Not part of the intended path. `meta` carries provider + options from an upstream Generate for chaining. An explicit `provider` or `options` wins over `meta`. |

- **`max_tokens` `0`** omits this face cap (host default). On Advanced, `0` leaves an Options or `meta` token limit in place if one is already there. **`1` or more** replaces that limit and is sent.
- **OpenAI** (`backend` `openai`): the face value is sent as `max_completion_tokens`. Other hosts get `max_tokens`. A legacy Options `max_tokens` toggle still sends `max_tokens`. If both fields are set, `max_completion_tokens` wins. Sampling params are not stripped for cloud. No native Anthropic.
- Temperature is not on this face. Host default applies unless a legacy Basic or Options node sets it.
- **Unload on interrupt** is not a face widget. Right-click the node → **Properties** → **Unload on interrupt** (`unload_on_interrupt`, default off). See [Cancel during generation](#cancel-during-generation).
- **Meta chaining:** connect `meta` out to the next Generate `meta` in. The model stays loaded across the chain and unloads only after the last node, when Manage VRAM (or a legacy lifecycle) is managing it.

### Utility Nodes

| Node | Description |
|------|-------------|
| **LLM Preset Loader** | Lists `.txt` files from the [`presets/`](presets/) directory, outputs file content as STRING |
| **LLM Load Text File** | Lists `.txt` files from ComfyUI's input folder, outputs file content as STRING |

Connect either to a generation node's `system_prompt` or `prompt` input. See [`presets/README.txt`](presets/README.txt) for format; shipped example [`presets/llamacpp_oai_system.txt`](presets/llamacpp_oai_system.txt) (llama.cpp / OAI Compatible).

### Legacy / compatibility

These nodes stay registered. They are not the intended new-graph path.

| Node | Role | Notes |
|------|------|-------|
| **LLM Generate (Basic)** | Compact generate | Required `provider`, inline `temperature` / `max_tokens` / `seed`. Same `0` = omit cap, and the same Properties interrupt flag. Use Advanced for new graphs. |
| **LLM Options: LM Studio** | Sampling wall | temperature, top_p, max_tokens, seed, stop, top_k, repeat_penalty, presence_penalty, frequency_penalty. Toggles. |
| **LLM Options: OpenAI** | Sampling wall | Core Chat Completions: temperature, top_p, max_tokens, max_completion_tokens, seed, stop, presence_penalty, frequency_penalty. Toggles. |
| **LLM Options: Textgen** | Sampling wall | temperature, top_p, max_tokens, seed, stop, top_k, min_p, repeat_penalty, presence_penalty, frequency_penalty, typical_p, tfs. Toggles. |
| **LLM Provider: OAI Compatible** | OpenAI-style HTTP (detected at `url`) | Optional `lifecycle` input; models via `POST /llm-bikeshed/models/oai-compat` |
| **LLM Provider: Textgen** | Textgen-only URL + its own memory toggle | Models via `POST /llm-bikeshed/models/textgen` (no fingerprinting) |
| **LLM Lifecycle: LM Studio** | TTL + `context_length` into OAI Compatible | Same idea as Connection's LM Studio face while Manage VRAM is ON |
| **LLM Lifecycle: Textgen** | `manage_model_memory` into OAI Compatible | Same idea as Connection **Manage VRAM** on a Textgen face |

Options output `LLM_OPTIONS`. Only toggled-on parameters are included. Unsupported parameters are dropped (info log). You do not need an Options node to set `max_tokens`: that knob is on **LLM Generate (Advanced)**. Connect Options only on an old graph that still wants the extra sampling keys. A face `max_tokens` of `1` or more replaces an Options token limit; `0` keeps it.

Without a lifecycle connection on **OAI Compatible**, and with **Manage VRAM** OFF on **Connection** (or **Manage model memory** OFF on the legacy **Textgen** provider), the adapter does not run Textgen load/unload. Connection Manage VRAM OFF on an LM Studio face also skips LM Studio load, TTL, and unload.

Shared legacy provider behavior: dynamic model dropdown + **Refresh Models** (first auto-fetch debounced ~600ms); `model_fallback` STRING override; read-only backend / loaded labels where applicable. Fingerprinting on **OAI Compatible** may still show **Ollama** as a label; this pack does not ship Ollama-native generation.

## Quick Start

### New graph (LLM Connection → Generate Advanced)

1. Add **LLM Connection**. Leave `host_mode` on **Auto (detect)** (or pin your backend).
2. Set `url` to your server base (LM Studio default `http://localhost:1234`, Textgen `http://localhost:5000`). Do **not** append `/v1`.
3. Click **Refresh Models**, pick a model (or type an id for llama.cpp / generic). Changing the model does not load weights.
4. For Textgen or LM Studio, leave **Manage VRAM** ON (default). LM Studio also shows **TTL** and **context length** while that toggle is ON. OpenAI, generic, and llama.cpp hide the toggle; chat still runs. llama.cpp status says router `/models/load` + `/models/unload` are not verified, so the pack will not load or unload that host.
5. Add **LLM Generate (Advanced)**. Connect Connection `provider` → Advanced `provider`.
6. Set `max_tokens` (default 1024; `0` omits the cap) and `seed` (sent even when `0`). Type the prompt and queue.

Open [`example_workflows/connection_generate.json`](example_workflows/connection_generate.json). Prompt text can also come from **LLM Load Text File** or **LLM Preset Loader**.

### llama.cpp via LLM Connection

Point Connection at any llama.cpp server that speaks OpenAI-compatible HTTP. There is no dedicated llama-server node.

1. Start the server so it exposes at least `/v1/chat/completions` (and ideally `/health` + `/v1/models`). Example: `llama-server --port 8080` (flags vary by build).
2. Add **LLM Connection**; set `host_mode` to **llama.cpp** or leave Auto.
3. Set `url` to the **base** URL **without** a duplicated `/v1` suffix — e.g. `http://127.0.0.1:8080`.
4. Click **Refresh Models** (type a model id when the catalog is empty). **Manage VRAM** stays hidden: this pack does not call llama.cpp router load/unload. Connect **LLM Generate (Advanced)** and queue a short prompt.

### Chaining Generations

1. Wire the first Generate node's `meta` output to the next Generate node's `meta` input
2. The model stays loaded across the chain when **Manage VRAM** (or a legacy lifecycle) is managing it
3. Only the last node in the chain triggers model unload or the short LM Studio TTL

### Older examples (migration)

These files stay in the repo so old graphs have a picture to copy from. They are not the new-graph path.

| File | Graph |
|------|--------|
| [`connection_basic.json`](example_workflows/connection_basic.json) | Connection + **Basic** |
| [`basic_generation.json`](example_workflows/basic_generation.json) | Legacy OAI Compatible + Basic |
| [`textgen_basic.json`](example_workflows/textgen_basic.json) | Legacy Textgen provider + Basic |
| [`advanced_with_options.json`](example_workflows/advanced_with_options.json) | Legacy OAI Compatible + Options + Advanced |

## Cancel during generation

Pressing **Cancel** in ComfyUI stops the generation node and lets the queue continue - the pack polls ComfyUI's interrupt flag and aborts in-flight HTTP.

- **Textgen:** the pack also calls Textgen's stop-generation endpoint when configured with an API key. This usually stops generation on the host, but behavior with non-streaming chat is not fully verified.
- **LM Studio / OpenAI / other OAI hosts:** Cancel unblocks ComfyUI, but the backend may keep running until it finishes on its own. There is no stop API wired for LM Studio in this pack.
- **VRAM cleanup on Cancel:** off unless you turn it on. Right-click a Generate node → **Properties** → **Unload on interrupt** (`unload_on_interrupt`). When that is on, Cancel unloads only if **Manage VRAM** (or a legacy lifecycle) is managing the model. Manage VRAM OFF never unloads. The default is off, including API queues that do not send the workflow properties blob.

## Architecture

- **VRAM / model memory (current behavior)** - **Connection** uses one **Manage VRAM** toggle. **Textgen** (toggle ON, or legacy Textgen provider / lifecycle wired to OAI Compatible): model list and loaded label use internal HTTP (`GET /v1/internal/model/list`, `GET /v1/internal/model/info`); generation uses `POST {url}/v1/chat/completions`; the adapter calls `POST {url}/v1/internal/model/load` / `unload` around generation. Chain-aware unload deferral uses **`skip_unload`** on generation nodes. Toggle OFF: no pack load/unload. **LM Studio** (toggle ON, or the legacy lifecycle node): TTL on chat and optional `context_length` on `POST /api/v1/models/load`; toggle OFF skips that. **llama.cpp:** chat via `/v1/chat/completions` only; Manage VRAM is hidden because router `/models/load` + `/models/unload` are not verified. **Ollama** is not supported natively in this pack. Legacy Lifecycle nodes stay registered.
- **Adapter pattern** - OpenAI-Compatible adapter: `POST {url}/v1/chat/completions`; optional lifecycle hooks for LM Studio (`/api/v1/models`, `ttl`) and Textgen (`/v1/internal/model/*`) when lifecycle is present (integrated on Connection / Textgen provider, or via **LLM Lifecycle** -> **OAI Compatible**)
- **Backend detection** - `detection.py` plus Connection `host_mode` / `POST /llm-bikeshed/models/connection`; legacy `POST /llm-bikeshed/detect` and `POST /llm-bikeshed/models/oai-compat` for OAI Compatible; **LLM Provider: Textgen** uses `POST /llm-bikeshed/models/textgen`
- **Synchronous HTTP** via `requests` (ComfyUI nodes run synchronously)
- **Config merge-on-load**: `config.example.yaml` defaults deep-merged with user's `config.yaml`
- **Frontend JS** for dynamic model dropdowns via PromptServer endpoints (`POST /llm-bikeshed/*`). These **client-server** routes are **not ComfyUI API-mode compatible**; generation still runs from graph dataflow (`LLM_PROVIDER` -> generate -> `/v1/chat/completions`). Headless queues need URL/model already set in the workflow JSON.

## Out of scope (current release)

- Image/vision describe nodes
- Chat/conversation history nodes
- Structured output (JSON schema enforcement)
- Full OpenAI API surface (tools, streaming, JSON mode, etc.) - only core chat sampling params in v0; additional cloud providers (Anthropic, Gemini, etc.)
- Streaming output
- vLLM-specific nodes and a dedicated llama-server / process-manager node (llama.cpp via Connection / OAI Compatible `/v1` is supported)
- Native Ollama in this pack (removed 0.3.0)

## Development

```bash
pip install -e ".[dev]"
python -m pytest -q
ruff check .
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for pull requests and issue reporting.

## ComfyUI Registry

Published on the [ComfyUI Registry](https://registry.comfy.org/nodes/comfyui-llm-bikeshed). Install via ComfyUI Manager (search `@amvir/comfyui-llm-bikeshed` or use the [registry listing](https://registry.comfy.org/nodes/comfyui-llm-bikeshed)), or clone into `custom_nodes/` as above.

**Publisher setup (one-time):**

1. Create a publisher at [registry.comfy.org](https://registry.comfy.org) (ID is permanent).
2. Create a **Registry Publishing API Key** for that publisher.
3. Set `PublisherId` under `[tool.comfy]` in `pyproject.toml` to your registry ID.
4. Publish: `pip install comfy-cli` then `comfy node publish` (prompts for API key), or add the registry API key as GitHub secret **`REGISTRY_ACCESS_TOKEN`** (official name; `COMFY_REGISTRY_API_KEY` also works in our workflow) and push a `pyproject.toml` change (see `.github/workflows/publish_registry.yml`).

## License

MIT - see [LICENSE](LICENSE).

