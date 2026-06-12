# ComfyUI LLM Bikeshed

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Tests](https://github.com/VirusShell/comfyui-llm-bikeshed/actions/workflows/test.yml/badge.svg)](https://github.com/VirusShell/comfyui-llm-bikeshed/actions/workflows/test.yml)

ComfyUI custom nodes for local LLM text generation. Use **LLM Provider: OAI Compatible** for OpenAI-style backends with automatic detection at the URL (LM Studio, OpenAI, llama.cpp, etc.). Use **LLM Provider: Textgen** for [oobabooga Textgen](https://github.com/oobabooga/text-generation-webui) (fixed backend, integrated VRAM controls, Textgen-only model list). API keys live in config or environment variables only.

**Product direction:** See [`docs/proposals/product-direction-and-scope.md`](docs/proposals/product-direction-and-scope.md) for scope notes (Textgen-first, lifecycle model under review, llama.cpp deferred).

## Features

- **2 Provider nodes** — **OAI Compatible** (auto-detected backend at URL) and **Textgen** (dedicated Textgen URL, `manage_model_memory` on-node, model list without fingerprinting)
- **2 Lifecycle nodes** (optional, legacy for Textgen when using OAI provider) — VRAM-aware LM Studio TTL/context or separate Textgen load/unload when wired into the OAI provider’s `lifecycle` input
- **2 Generation nodes** — Basic (compact, inline params) and Advanced (modular, connection-driven)
- **3 Options nodes** — LM Studio, Textgen, and OpenAI core sampling parameters
- **2 Utility nodes** — Preset Loader and Load Text File
- **VRAM-aware** — **Textgen:** enable **Manage model memory** on **LLM Provider: Textgen** (or connect **LLM Lifecycle: Textgen** to **OAI Compatible**) so the adapter loads before chat and unloads after the last generation in a chain. **LM Studio:** optional lifecycle TTL
- **Secure** — API keys from config file or environment variables, never in workflow JSON
- **Minimal dependencies** — only `pyyaml` and `requests` (no provider SDKs)

## Requirements

- ComfyUI (V1 node spec)
- Python 3.10+
- At least one LLM backend running, for example:
  - [LM Studio](https://lmstudio.ai/) (default: `http://localhost:1234`)
  - [Textgen / text-generation-webui](https://github.com/oobabooga/text-generation-webui) (default: `http://localhost:5000`) — verified HTTP/auth for internal model routes is summarized in [`docs/research/textgen-lifecycle-verified.md`](docs/research/textgen-lifecycle-verified.md). **VRAM / model memory today:** see the same doc (appendix) and the short summary under [Architecture](#architecture).
  - Optional: **OpenAI** (`https://api.openai.com`) — set `providers.openai.api_key` or `LLM_BIKESHED_OPENAI_API_KEY`; keys never stored in workflows

Native **Ollama** (`/api/chat`) is not supported by this pack; use a dedicated Ollama-focused custom node pack, or an OpenAI-compatible gateway if your stack exposes `/v1/chat/completions`.

## Installation

1. Clone or download this repository into your ComfyUI `custom_nodes/` directory:

   ```bash
   cd ComfyUI/custom_nodes
   git clone https://github.com/VirusShell/comfyui-llm-bikeshed.git
   ```

2. Install dependencies:

   ```bash
   cd comfyui-llm-bikeshed
   pip install -r requirements.txt
   ```

   Or manually: `pip install pyyaml>=6.0 requests>=2.28.0`

3. Restart ComfyUI. Nodes appear under the **LLM Bikeshed** category.

Example workflows are in [`example_workflows/`](example_workflows/) — load them from ComfyUI's template browser or via **Load** to get started quickly.

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
       # Fallback keys for OAI Compatible node (OpenAI, proxies, or when probing Textgen).
       # api_key: "your-api-key-here"
   ```

3. `config.yaml` is gitignored — your keys and overrides stay local.

   Legacy `providers.ollama` keys in an existing `config.yaml` are ignored by this pack (deep-merge preserves them; you may delete that block manually).

### API Key Resolution

Keys are resolved in this order (first match wins):

1. `config.yaml` provider entry (`api_key` / `admin_key`)
2. Environment variable: `LLM_BIKESHED_{PROVIDER}_API_KEY` (e.g., `LLM_BIKESHED_LM_STUDIO_API_KEY`)
3. None (local backends typically need no key)

API keys never appear in workflow JSON — Provider nodes have no key widget.

## Nodes

### Provider Nodes

Configure a backend connection. Each outputs an `LLM_PROVIDER` type.

| Node | Role | Key settings |
|------|------|----------------|
| **LLM Provider: OAI Compatible** | OpenAI-style HTTP backends (detected at `url`) | `url`, `model` dropdown, optional `lifecycle` input — API keys from config/env per detected backend + `oai_compat` fallback |
| **LLM Provider: Textgen** | oobabooga Textgen only (`text_gen_webui` + `oai_compat` adapter) | `url` (default `http://localhost:5000`), `model`, **`manage_model_memory`** (ON = same lifecycle as **LLM Lifecycle: Textgen** — load/unload around generation), optional `model_fallback` — keys via `get_textgen_auth_keys()` |

For **Textgen**, queuing a generation with **Manage model memory** ON loads the selected model automatically (no separate load control). Use **Refresh Models** to refresh the dropdown and the read-only **loaded** line.

**Migration:** Replace **LLM Provider: OAI Compatible** + **LLM Lifecycle: Textgen** with **LLM Provider: Textgen** (`manage_model_memory` ON) for the same VRAM behavior and simpler graphs.

All provider nodes share:

- Dynamic model dropdown (queries backend via PromptServer; **Refresh Models** button). The first auto-fetch is **debounced** (~600ms) so rapid node creation does not duplicate requests or flood logs when the default URL is offline. **Textgen** lists use **`GET /v1/internal/model/list`** first (same models as the Textgen UI), then fall back to **`GET /v1/models`** if needed. The dedicated Textgen provider calls **`POST /llm-bikeshed/models/textgen`** (skips multi-backend detection for speed and quieter logs).
- `model_fallback` STRING input — overrides dropdown when connected (useful when backend is offline)

The read-only **detected backend** label on provider nodes can still show **Ollama** on **OAI Compatible** when URL fingerprinting matches Ollama’s `/api/version` shape; **LLM Provider: Textgen** always reports Textgen. This pack does not ship Ollama-native nodes or routes—use another pack or an OAI-compatible path for generation.

### Lifecycle nodes (optional)

Use with **LLM Provider: OAI Compatible** when you want LM Studio TTL or a **separate** Textgen lifecycle widget. **LLM Lifecycle: Textgen** remains supported for old graphs but is **legacy** if you use **LLM Provider: Textgen** — that provider includes the same `manage_model_memory` behavior on-node.

Without a lifecycle connection on **OAI Compatible** (and with **Manage model memory** OFF on **LLM Provider: Textgen**), the adapter does not run local Textgen load/unload.

| Node | When to use | Widgets |
|------|-------------|---------|
| **LLM Lifecycle: LM Studio** | Detected backend is LM Studio | `ttl`, `context_length` |
| **LLM Lifecycle: Textgen** | **Legacy** when using **OAI Compatible** at a Textgen URL; prefer **LLM Provider: Textgen** with **Manage model memory** for new workflows | `manage_model_memory` (ON = enable load/unload; OFF = same as no lifecycle node) |

### Generation Nodes

Produce text from an LLM. Both output `text` (STRING) and `meta` (LLM_META).

| Node | Style | Inputs |
|------|-------|--------|
| **LLM Generate (Basic)** | Compact | `provider`, `prompt`, `system_prompt`, inline `temperature`/`max_tokens`/`seed` |
| **LLM Generate (Advanced)** | Modular | `provider`, `prompt`, `system_prompt`, `options` (LLM_OPTIONS), `meta` (LLM_META) |

- **Basic** works without an Options node — inline params are sufficient.
- **Advanced** accepts everything via connections. No inline inference params.
- **Meta chaining**: connect `meta` output to the next generation node's `meta` input. The model stays loaded across the chain and unloads only after the last node.

### Options Nodes

Configure inference parameters. All output `LLM_OPTIONS` type.

| Node | Backend | Parameters | Pattern |
|------|---------|-----------|---------|
| **LLM Options: LM Studio** | LM Studio | temperature, top_p, max_tokens, seed, stop, top_k, repeat_penalty, presence_penalty, frequency_penalty | Boolean toggles (ON/OFF) |
| **LLM Options: OpenAI** | OpenAI API | Core Chat Completions: temperature, top_p, max_tokens, max_completion_tokens, seed, stop, presence_penalty, frequency_penalty | Boolean toggles (ON/OFF) |
| **LLM Options: Textgen** | text-generation-webui | temperature, top_p, max_tokens, seed, stop, top_k, min_p, repeat_penalty, presence_penalty, frequency_penalty, typical_p, tfs | Boolean toggles (ON/OFF) |

- Options nodes are always optional — disconnect them and the model uses its own defaults.
- Unsupported parameters are silently dropped (logged at info level).

### Utility Nodes

| Node | Description |
|------|-------------|
| **LLM Preset Loader** | Lists `.txt` files from the `presets/` directory, outputs file content as STRING |
| **LLM Load Text File** | Lists `.txt` files from ComfyUI's input folder, outputs file content as STRING |

Connect either to a generation node's `system_prompt` or `prompt` input.

## Quick Start

### Minimal Setup (Basic Generation)

1. Add **LLM Provider: Textgen** (or **OAI Compatible** for mixed backends), point `url` at Textgen (default `http://localhost:5000`)
2. Leave **Manage model memory** ON on **LLM Provider: Textgen** so the model loads when you queue the graph (or connect **LLM Lifecycle: Textgen** → **OAI Compatible** if you still use the generic provider)
3. Add **LLM Generate (Basic)**
4. Connect Provider output to Generate's `provider` input
5. Type your prompt and system prompt
6. Queue the workflow

### Advanced Setup (Modular Generation)

1. Add a **Provider** node
2. Add **LLM Options** node matching your backend
3. Add **LLM Generate (Advanced)**
4. Connect: Provider -> `provider`, Options -> `options`
5. Connect prompt text via **LLM Load Text File** or type directly

### Chaining Generations

1. Wire first generation node's `meta` output to second generation node's `meta` input
2. The model stays loaded across the chain (VRAM-aware deferral)
3. Only the last node in the chain triggers model unload/short TTL

## Architecture

- **VRAM / model memory (current behavior)** — **Textgen:** model list and loaded label use internal HTTP (`GET /v1/internal/model/list`, `GET /v1/internal/model/info`); generation uses `POST {url}/v1/chat/completions`; with **Manage model memory** ON (dedicated Textgen provider or lifecycle wired to OAI Compatible), the adapter calls `POST {url}/v1/internal/model/load` / `unload` around generation. Chain-aware unload deferral uses **`skip_unload`** on generation nodes. **LM Studio:** TTL/context via the LM Studio lifecycle node. **Ollama** is not supported natively in this pack. **Still open:** lifecycle UX long-term; see [`docs/proposals/product-direction-and-scope.md`](docs/proposals/product-direction-and-scope.md).
- **Adapter pattern** — OpenAI-Compatible adapter: `POST {url}/v1/chat/completions`; optional lifecycle hooks for LM Studio (`/api/v1/models`, `ttl`) and Textgen (`/v1/internal/model/*`) when lifecycle is present on the provider (integrated on **LLM Provider: Textgen** when **Manage model memory** is ON, or via **LLM Lifecycle** → **OAI Compatible**)
- **Backend detection** — `detection.py` plus `POST /llm-bikeshed/detect` for the indicator on the OAI Compatible provider; **LLM Provider: Textgen** uses `POST /llm-bikeshed/models/textgen` (no fingerprinting) for the model dropdown
- **Synchronous HTTP** via `requests` (ComfyUI nodes run synchronously)
- **Config merge-on-load**: `config.example.yaml` defaults deep-merged with user's `config.yaml`
- **Frontend JS** for dynamic model dropdowns via PromptServer endpoints

## Out of scope (current release)

- Image/vision describe nodes
- Chat/conversation history nodes
- Structured output (JSON schema enforcement)
- Full OpenAI API surface (tools, streaming, JSON mode, etc.) — only core chat sampling params in v0; additional cloud providers (Anthropic, Gemini, etc.)
- Streaming output
- vLLM and standalone llama-server backends
- Native Ollama in this pack (removed 0.3.0)

## Development

```bash
pip install -e ".[dev]"
python -m pytest -q
ruff check .
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for pull requests and issue reporting.

## ComfyUI Registry

Install via ComfyUI-Manager once published, or clone into `custom_nodes/` as above.

**Publisher setup (one-time):**

1. Create a publisher at [registry.comfy.org](https://registry.comfy.org) (ID is permanent).
2. Create a **Registry Publishing API Key** for that publisher.
3. Set `PublisherId` under `[tool.comfy]` in `pyproject.toml` to your registry ID.
4. Publish: `pip install comfy-cli` then `comfy node publish` (prompts for API key), or add `REGISTRY_ACCESS_TOKEN` to GitHub Actions secrets and push a `pyproject.toml` version bump (see `.github/workflows/publish_registry.yml`).

## License

MIT — see [LICENSE](LICENSE).
