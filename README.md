# ComfyUI LLM Bikeshed

ComfyUI custom nodes for local LLM text generation. Use **LLM Provider: OAI Compatible** for OpenAI-style backends (LM Studio, Textgen, OpenAI, llama.cpp, etc.) with automatic detection at the URL. API keys live in config or environment variables only.

**Product direction:** See [`docs/proposals/product-direction-and-scope.md`](docs/proposals/product-direction-and-scope.md) for scope notes (Textgen-first, lifecycle model under review, llama.cpp deferred).

## Features

- **1 Provider node** — OAI Compatible (auto-detected backend at URL, including OpenAI API when configured)
- **2 Lifecycle nodes** (optional) — VRAM-aware LM Studio TTL/context or Textgen load/unload when wired into the OAI provider’s `lifecycle` input
- **2 Generation nodes** — Basic (compact, inline params) and Advanced (modular, connection-driven)
- **3 Options nodes** — LM Studio, Textgen, and OpenAI core sampling parameters
- **2 Utility nodes** — Preset Loader and Load Text File
- **VRAM-aware** — optional lifecycle nodes gate explicit model load/unload (Textgen, LM Studio)
- **Secure** — API keys from config file or environment variables, never in workflow JSON
- **Minimal dependencies** — only `pyyaml` and `requests` (no provider SDKs)

## Requirements

- ComfyUI (V1 node spec)
- Python 3.10+
- At least one LLM backend running, for example:
  - [LM Studio](https://lmstudio.ai/) (default: `http://localhost:1234`)
  - [Textgen / text-generation-webui](https://github.com/oobabooga/text-generation-webui) (default: `http://localhost:5000`)
  - Optional: **OpenAI** (`https://api.openai.com`) — set `providers.openai.api_key` or `LLM_BIKESHED_OPENAI_API_KEY`; keys never stored in workflows

Native **Ollama** (`/api/chat`) is not supported by this pack; use a dedicated Ollama-focused custom node pack, or an OpenAI-compatible gateway if your stack exposes `/v1/chat/completions`.

## Installation

1. Clone or download this repository into your ComfyUI `custom_nodes/` directory:

   ```bash
   cd ComfyUI/custom_nodes
   git clone https://github.com/your-username/comfyui-llm-bikeshed.git
   ```

2. Install dependencies:

   ```bash
   cd comfyui-llm-bikeshed
   pip install -r requirements.txt
   ```

   Or manually: `pip install pyyaml>=6.0 requests>=2.28.0`

3. Restart ComfyUI. Nodes appear under the **LLM Bikeshed** category.

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

### Config Reload

Config can be reloaded without restarting ComfyUI via the PromptServer endpoint:

```
POST /llm-bikeshed/reload-config
```

## Nodes

### Provider Nodes

Configure a backend connection. Each outputs an `LLM_PROVIDER` type.

| Node | Role | Key settings |
|------|------|----------------|
| **LLM Provider: OAI Compatible** | OpenAI-style HTTP backends (detected at `url`) | `url`, `model` dropdown, optional `lifecycle` input — API keys from config/env per detected backend + `oai_compat` fallback |

All provider nodes have:
- Dynamic model dropdown (queries backend via PromptServer; refresh button). Initial fetch is deferred one microtask so saved workflow values apply before the list updates. For **Textgen**, the server asks **`GET /v1/internal/model/list`** first (same models as the Textgen UI), then falls back to **`GET /v1/models`** if needed.
- `model_fallback` STRING input — overrides dropdown when connected (useful when backend is offline)

The read-only **detected backend** label (OAI node only) can still show **Ollama** when URL fingerprinting matches Ollama’s `/api/version` shape; this pack does not ship Ollama-native nodes or routes—use another pack or an OAI-compatible path for generation.

### Lifecycle nodes (optional)

Use only with **LLM Provider: OAI Compatible**. Connect the `lifecycle` output to the provider’s optional `lifecycle` input to turn on explicit VRAM management for **LM Studio** or **Textgen** when that backend is detected. Without a lifecycle connection, the adapter does not run local load/unload.

| Node | When to use | Widgets |
|------|-------------|---------|
| **LLM Lifecycle: LM Studio** | Detected backend is LM Studio | `ttl`, `context_length` |
| **LLM Lifecycle: Textgen** | Detected backend is Textgen | `manage_model_memory` (ON = enable load/unload; OFF = same as no lifecycle node). A widget is required so ComfyUI draws the node body reliably. |

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

1. Add **LLM Provider: OAI Compatible** (point `url` at your LM Studio, Textgen, OpenAI-compatible server, etc.)
2. Add **LLM Generate (Basic)**
3. Connect Provider output to Generate's `provider` input
4. Type your prompt and system prompt
5. Queue the workflow

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

- **Adapter pattern** — OpenAI-Compatible adapter: `POST {url}/v1/chat/completions`; optional lifecycle hooks for LM Studio (`/api/v1/models`, `ttl`) and Textgen (`/v1/internal/model/*`) when a matching lifecycle node is connected
- **Backend detection** — `detection.py` plus `POST /llm-bikeshed/detect` for the indicator on the OAI Compatible provider (includes fingerprinting that may label a host as Ollama even though this pack does not run native Ollama chat)
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

## License

MIT
