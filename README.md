# ComfyUI LLM Bikeshed

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Tests](https://github.com/VirusShell/comfyui-llm-bikeshed/actions/workflows/test.yml/badge.svg)](https://github.com/VirusShell/comfyui-llm-bikeshed/actions/workflows/test.yml)

ComfyUI custom nodes for local LLM text generation. Prefer **LLM Connection** for new graphs: one adaptive node with host mode (Auto or pinned backend), URL/model, and on-node VRAM knobs for Textgen / LM Studio. API keys live in config or environment variables only — never in workflow JSON.

**Legacy / old graphs:** **LLM Provider: OAI Compatible**, **LLM Provider: Textgen**, and the separate **Lifecycle** nodes remain registered so existing workflows keep working. Prefer **LLM Connection** instead of Provider + Lifecycle for new work.

**Product direction:** See [`docs/proposals/product-direction-and-scope.md`](docs/proposals/product-direction-and-scope.md) for scope notes (Textgen-first, lifecycle model under review; llama.cpp via Connection or OAI Compatible is first-class; dedicated llama-server node deferred).

## Features

- **LLM Connection** (recommended) - Adaptive host mode (Auto detect or pin LM Studio / Textgen / llama.cpp / OpenAI / Generic OAI), shared URL + model face, embedded Textgen/LM Studio VRAM knobs, secret-free status chrome; models via `POST /llm-bikeshed/models/connection`
- **2 Generation nodes** - Basic (compact, inline params) and Advanced (modular, connection-driven)
- **3 Options nodes** - LM Studio, Textgen, and OpenAI core sampling parameters
- **2 Utility nodes** - Preset Loader and Load Text File
- **VRAM-aware** - **Textgen** / **LM Studio** faces on Connection (or legacy Provider + Lifecycle) load/unload or TTL around generation; chain-aware unload via `meta`
- **Secure** - API keys from config file or environment variables, never in workflow JSON
- **Minimal dependencies** - only `pyyaml` and `requests` (no provider SDKs)
- **Legacy / old graphs** - **OAI Compatible** and **Textgen** provider nodes plus optional Lifecycle nodes stay registered (see [Legacy / old graphs](#legacy--old-graphs))

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

Example workflows are in [`example_workflows/`](example_workflows/) - load them from ComfyUI's template browser or via **Load** to get started quickly. Start with [`connection_basic.json`](example_workflows/connection_basic.json).

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
| `manage_model_memory` | Textgen face: load before generate / unload after chain when ON |
| `ttl` / `context_length` | LM Studio face: keep-alive TTL and optional context on load |
| `ensure_load_on_select` | Textgen/LM Studio: optional load when the model dropdown changes (default OFF; URL changes never load) |
| `model_fallback` | Optional STRING input - overrides dropdown when connected |
| `timeout` | Advanced; `0` = config for effective backend, then `oai_compat`, then 120 |

**Refresh Models** calls `POST /llm-bikeshed/models/connection` with `{ "url", "host_mode" }` and updates the model widget plus read-only status lines (detected / effective backend, loaded model, auth hint). No separate Lifecycle node is required for new graphs.

**Migration:** Replace **Provider** (+ optional **Lifecycle**) with **LLM Connection**. Wire `provider` into Generate the same way.

### Generation Nodes

Produce text from an LLM. Both output `text` (STRING) and `meta` (LLM_META).

| Node | Style | Inputs |
|------|-------|--------|
| **LLM Generate (Basic)** | Compact | `provider`, `prompt`, `system_prompt`, inline `temperature`/`max_tokens`/`seed` |
| **LLM Generate (Advanced)** | Modular | `provider`, `prompt`, `system_prompt`, `options` (LLM_OPTIONS), `meta` (LLM_META) |

- **Basic** works without an Options node - inline params are sufficient.
- **Advanced** accepts everything via connections. No inline inference params.
- **Meta chaining**: connect `meta` output to the next generation node's `meta` input. The model stays loaded across the chain and unloads only after the last node.

### Options Nodes

Configure inference parameters. All output `LLM_OPTIONS` type.

| Node | Backend | Parameters | Pattern |
|------|---------|-----------|---------|
| **LLM Options: LM Studio** | LM Studio | temperature, top_p, max_tokens, seed, stop, top_k, repeat_penalty, presence_penalty, frequency_penalty | Boolean toggles (ON/OFF) |
| **LLM Options: OpenAI** | OpenAI API | Core Chat Completions: temperature, top_p, max_tokens, max_completion_tokens, seed, stop, presence_penalty, frequency_penalty | Boolean toggles (ON/OFF) |
| **LLM Options: Textgen** | text-generation-webui | temperature, top_p, max_tokens, seed, stop, top_k, min_p, repeat_penalty, presence_penalty, frequency_penalty, typical_p, tfs | Boolean toggles (ON/OFF) |

- Options nodes are always optional - disconnect them and the model uses its own defaults.
- Unsupported parameters are silently dropped (logged at info level).

### Utility Nodes

| Node | Description |
|------|-------------|
| **LLM Preset Loader** | Lists `.txt` files from the [`presets/`](presets/) directory, outputs file content as STRING |
| **LLM Load Text File** | Lists `.txt` files from ComfyUI's input folder, outputs file content as STRING |

Connect either to a generation node's `system_prompt` or `prompt` input. See [`presets/README.txt`](presets/README.txt) for format; shipped example [`presets/llamacpp_oai_system.txt`](presets/llamacpp_oai_system.txt) (llama.cpp / OAI Compatible).

### Legacy / old graphs

These nodes stay registered for existing workflows. Prefer **LLM Connection** for new graphs.

| Node | Role | Notes |
|------|------|-------|
| **LLM Provider: OAI Compatible** | OpenAI-style HTTP backends (detected at `url`) | Optional `lifecycle` input; models via `POST /llm-bikeshed/models/oai-compat` |
| **LLM Provider: Textgen** | Textgen-only URL + on-node `manage_model_memory` | Models via `POST /llm-bikeshed/models/textgen` (no fingerprinting) |
| **LLM Lifecycle: LM Studio** | TTL + `context_length` into OAI Compatible `lifecycle` | Embedded on Connection's LM Studio face |
| **LLM Lifecycle: Textgen** | `manage_model_memory` into OAI Compatible `lifecycle` | Prefer Connection or Textgen provider for new work |

Without a lifecycle connection on **OAI Compatible** (and with **Manage model memory** OFF on **Textgen** / Connection Textgen face), the adapter does not run local Textgen load/unload.

Shared legacy provider behavior: dynamic model dropdown + **Refresh Models** (first auto-fetch debounced ~600ms); `model_fallback` STRING override; read-only backend / loaded labels where applicable. Fingerprinting on **OAI Compatible** may still show **Ollama** as a label; this pack does not ship Ollama-native generation.

## Quick Start

### Minimal Setup (LLM Connection)

1. Add **LLM Connection**. Leave `host_mode` on **Auto (detect)** (or pin your backend).
2. Set `url` to your server base (LM Studio default `http://localhost:1234`, Textgen `http://localhost:5000`). Do **not** append `/v1`.
3. Click **Refresh Models**, pick a model (or type an id for llama.cpp / generic).
4. For Textgen, leave **Manage model memory** ON so the model loads when you queue. For LM Studio, set **TTL** as needed.
5. Add **LLM Generate (Basic)**, connect Connection `provider` -> Generate `provider`.
6. Type your prompt and system prompt, queue the workflow.

See [`example_workflows/connection_basic.json`](example_workflows/connection_basic.json).

### llama.cpp via LLM Connection

Dedicated llama-server / process-manager nodes are **deferred**. Point Connection (or legacy OAI Compatible) at any llama.cpp server that speaks OpenAI-compatible HTTP.

1. Start the server so it exposes at least `/v1/chat/completions` (and ideally `/health` + `/v1/models`). Example: `llama-server --port 8080` (flags vary by build).
2. Add **LLM Connection**; set `host_mode` to **llama.cpp** or leave Auto.
3. Set `url` to the **base** URL **without** a duplicated `/v1` suffix - e.g. `http://127.0.0.1:8080`.
4. Click **Refresh Models** (string/type-in model when catalog is empty). Connect **LLM Generate (Basic)** and queue a short prompt.

### Advanced Setup (Modular Generation)

1. Add **LLM Connection**
2. Add **LLM Options** matching your backend
3. Add **LLM Generate (Advanced)**
4. Connect: Connection -> `provider`, Options -> `options`
5. Connect prompt text via **LLM Load Text File** or type directly

### Chaining Generations

1. Wire first generation node's `meta` output to second generation node's `meta` input
2. The model stays loaded across the chain (VRAM-aware deferral)
3. Only the last node in the chain triggers model unload/short TTL

## Cancel during generation

Pressing **Cancel** in ComfyUI stops the generation node and lets the queue continue - the pack polls ComfyUI's interrupt flag and aborts in-flight HTTP.

- **Textgen:** the pack also calls Textgen's stop-generation endpoint when configured with an API key. This usually stops generation on the host, but behavior with non-streaming chat is not fully verified.
- **LM Studio / OpenAI / other OAI hosts:** Cancel unblocks ComfyUI, but the backend may keep running until it finishes on its own. There is no stop API wired for LM Studio in this pack.
- **VRAM cleanup on Cancel:** not implemented yet. If you cancel mid-run, the model may stay loaded (Textgen) or follow the normal TTL (LM Studio) - same as if generation had completed without an explicit unload.

## Architecture

- **VRAM / model memory (current behavior)** - **Textgen:** model list and loaded label use internal HTTP (`GET /v1/internal/model/list`, `GET /v1/internal/model/info`); generation uses `POST {url}/v1/chat/completions`; with **Manage model memory** ON (Connection Textgen face, dedicated Textgen provider, or lifecycle wired to OAI Compatible), the adapter calls `POST {url}/v1/internal/model/load` / `unload` around generation. Chain-aware unload deferral uses **`skip_unload`** on generation nodes. **LM Studio:** TTL/context via Connection's LM Studio face or the LM Studio lifecycle node. **Ollama** is not supported natively in this pack. **Still open:** lifecycle UX long-term; see [`docs/proposals/product-direction-and-scope.md`](docs/proposals/product-direction-and-scope.md).
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

