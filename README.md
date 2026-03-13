# ComfyUI LLM Bikeshed

ComfyUI custom nodes for local LLM text generation. Connect your workflows to **Ollama**, **LM Studio**, and **text-generation-webui** with VRAM-aware model memory management.

## Features

- **3 Provider nodes** — one per backend, with dynamic model dropdowns
- **2 Generation nodes** — Basic (compact, inline params) and Advanced (modular, connection-driven)
- **4 Options nodes** — per-backend inference parameter control
- **2 Utility nodes** — Preset Loader and Load Text File
- **VRAM-aware** — short TTL/keep_alive defaults free GPU memory for Stable Diffusion after LLM generation
- **Secure** — API keys from config file or environment variables, never in workflow JSON
- **Minimal dependencies** — only `pyyaml` and `requests` (no provider SDKs)

## Requirements

- ComfyUI (V1 node spec)
- Python 3.10+
- At least one local LLM backend running:
  - [Ollama](https://ollama.ai/) (default: `http://localhost:11434`)
  - [LM Studio](https://lmstudio.ai/) (default: `http://localhost:1234`)
  - [text-generation-webui](https://github.com/oobabooga/text-generation-webui) (default: `http://localhost:5000`)

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
     ollama:
       url: "http://localhost:11434"
       timeout: 120

     lm_studio:
       url: "http://localhost:1234"
       timeout: 120
       # api_key: "your-api-key-here"

     text_gen_webui:
       url: "http://localhost:5000"
       timeout: 120
       # api_key: "your-api-key-here"
       # admin_key: "your-admin-key-here"
   ```

3. `config.yaml` is gitignored — your keys and overrides stay local.

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

| Node | Backend | Key Settings |
|------|---------|-------------|
| **LLM Provider: LM Studio** | LM Studio | `url`, `model` dropdown, `ttl` (seconds, default 30) |
| **LLM Provider: Ollama** | Ollama | `url`, `model` dropdown, `keep_alive` (string, default "30s") |
| **LLM Provider: text-gen-webui** | text-generation-webui | `url`, `model` dropdown |

All Provider nodes have:
- Dynamic model dropdown (queries running backend, refresh button)
- `model_fallback` STRING input — overrides dropdown when connected (useful when backend is offline)

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
| **LLM Options: Ollama (Core)** | Ollama | temperature, top_k, top_p, seed, num_predict, num_ctx, stop | Sentinel values (-1 = model default) |
| **LLM Options: Ollama (Extra)** | Ollama | mirostat, mirostat_eta, mirostat_tau, repeat_penalty, repeat_last_n, frequency_penalty, presence_penalty, tfs_z, typical_p, min_p | Boolean toggles (ON/OFF) |
| **LLM Options: LM Studio** | LM Studio | temperature, top_p, max_tokens, seed, stop, top_k, repeat_penalty, presence_penalty, frequency_penalty | Boolean toggles (ON/OFF) |
| **LLM Options: text-gen-webui** | text-gen-webui | temperature, top_p, max_tokens, seed, stop, top_k, min_p, repeat_penalty, presence_penalty, frequency_penalty, typical_p, tfs | Boolean toggles (ON/OFF) |

- Ollama Extra chains into Ollama Core via `options_in` input.
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

1. Add **LLM Provider: LM Studio** (or your backend of choice)
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

- **Adapter pattern**: Two adapters handle all three backends
  - Ollama Native — `POST {url}/api/chat`
  - OpenAI-Compatible — `POST {url}/v1/chat/completions` (LM Studio, text-gen-webui)
- **Synchronous HTTP** via `requests` (ComfyUI nodes run synchronously)
- **Config merge-on-load**: `config.example.yaml` defaults deep-merged with user's `config.yaml`
- **Frontend JS** for dynamic model dropdowns via PromptServer endpoints

## Out of Scope (v0.1.0)

- Image/vision describe nodes
- Chat/conversation history nodes
- Structured output (JSON schema enforcement)
- Cloud providers (OpenAI, Anthropic, Gemini, etc.)
- Streaming output
- vLLM and standalone llama-server backends

## License

MIT
