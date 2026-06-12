# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.0] - 2026-06-12

First public GitHub and ComfyUI Registry release. Core v1: OAI-compatible and Textgen providers, Basic/Advanced generation, per-provider options, lifecycle nodes, presets, and ComfyUI **Cancel** during LLM HTTP. Default branch is master.

### Security

- **Credentials no longer in execution outputs** — `LLM_PROVIDER` and `LLM_META` dicts no longer embed `api_key` / `admin_key`. Adapters resolve secrets from `config.yaml` / env at HTTP time via `config.auth.resolve_provider_auth`.
- **Removed unauthenticated `POST /llm-bikeshed/set-key`** — API keys must be set in `config.yaml` or environment variables; no runtime config writes from the browser.

### Removed

- **`write_api_key`** and **`POST /llm-bikeshed/set-key`** — unused by the frontend; posed an unauthenticated config write risk.
- **`POST /llm-bikeshed/reload-config`** — unused by the frontend; restart ComfyUI (or call `reload_config()` from Python) after editing `config.yaml`.

### Added

- **`example_workflows/`** — minimal template JSON files for basic generation, advanced options chaining, and Textgen.
- **`LICENSE`** — MIT license file (matches README and pyproject).
- **GitHub Actions CI** — `.github/workflows/test.yml` runs `pytest` and `ruff check` on push/PR.
- **`CONTRIBUTING.md`** — development setup, PR expectations, and scope notes for public GitHub contributors.
- **GitHub issue template** — minimal bug report form under `.github/ISSUE_TEMPLATE/`.

### Changed

- **Ruff cleanup** — fixed line length, unused import, and import sorting issues across the codebase.
- **Provenance audit abandoned** — backward inventory archived to `docs/the-archive/`; decision-time prevention docs remain authoritative.
- **README** — GitHub-oriented install URL, CI badge, development section, and ComfyUI Registry pointer.
- **`pyproject.toml`** — `readme`, `authors`, `keywords`, and GitHub `project.urls`.

## [0.3.0] - 2026-05-12

### Removed

- **Ollama as a first-class backend** — removed `OllamaAdapter` / `ollama_native`, `LLM Provider: Ollama`, `LLM Options: Ollama (Core)` and `(Extra)`, `POST /llm-bikeshed/models/ollama`, `PROVIDER_CONFIG.LLMProviderOllama` in `js/model_dropdown.js`, and `_fetch_models_ollama` plus the `providers.ollama` block from `config.example.yaml`. Workflows that still reference those node types will fail until rebuilt (use a dedicated Ollama pack or an OpenAI-compatible URL).

### Fixed

- **Options chaining** — `build_toggle_options` now reads `options_in` from `kwargs` so upstream options merge correctly for LM Studio and Textgen options nodes.

### Fixed

- **`model_list.py` shipped with the pack** — `server/endpoints.py` imports it for `POST /llm-bikeshed/models/oai-compat`, but the module was missing from the repo. Restores Textgen model dropdown behavior: when the detected backend is Textgen, the code prefers **`GET /v1/internal/model/list`** (matches the Textgen UI) before falling back to OpenAI-style **`GET /v1/models`**, with Bearer retries using `providers.text_gen_webui` / `oai_compat` keys via [`get_textgen_auth_keys`](config/__init__.py).

## [0.2.1] - 2026-05-10

### Fixed

- **LLM Lifecycle: Textgen** — added `manage_model_memory` BOOLEAN (default ON). Nodes with no widgets did not render inputs in ComfyUI; LM Studio lifecycle already had TTL/context widgets.

### Changed

- **Model dropdown** — initial model fetch runs after `queueMicrotask` so workflow-loaded COMBO values deserialize before the first refresh (reduces wrong or blank model labels after tab/graph switches).

## [0.2.0] - 2026-05-02

### Added

- **Backend auto-detection** — `detection.py` probes API endpoints to identify the backend at a URL (Ollama, llama.cpp, LM Studio, Textgen, OpenAI, or generic fallback).
- **Generic OAI-compatible provider** — single `LLM Provider: OAI Compatible` node replaces the three separate LM Studio, OpenAI, and Textgen provider nodes. Auto-detects backend and resolves API keys accordingly.
- **Composable lifecycle nodes** — `LLM Lifecycle: LM Studio` (TTL + context_length) and `LLM Lifecycle: Textgen` (presence-only) for opt-in VRAM management. Model management only activates when a lifecycle node is connected.
- **llama.cpp parameter allowlist** — llama.cpp backends now get a curated allowlist instead of dropping all params.
- **Generic backend passthrough** — unknown/unrecognized backends pass all JSON-safe params through unfiltered.
- **Backend detection endpoint** — `POST /llm-bikeshed/detect` returns the detected backend type for a URL.
- **API key entry endpoint** — `POST /llm-bikeshed/set-key` writes API keys to `config.yaml` from the frontend.
- **Consolidated model list endpoint** — `POST /llm-bikeshed/models/oai-compat` replaces the three per-backend model endpoints, with auth retry across all configured keys.
- **Backend indicator widget** — non-serialized `detected_backend` text widget on the OAI-compatible provider node shows the auto-detected backend type.
- **Detection tests** — 11 tests covering all backend detection paths and edge cases.
- **Lifecycle tests** — 5 tests for both lifecycle node types.

### Changed

- **Provider dict shape** — OAI-compat providers now use `lifecycle` key (dict or None) instead of `memory` key. Ollama provider unchanged (keeps `memory.keep_alive`).
- **Model management gating** — adapter load/unload calls are now gated on lifecycle presence AND lifecycle type matching the detected backend. No lifecycle = no model management.
- **Server endpoints** — removed `/llm-bikeshed/models/lm-studio`, `/models/openai`, `/models/text-gen-webui`; replaced by single `/models/oai-compat`.
- **JS frontend** — `PROVIDER_CONFIG` collapsed from 4 entries to 2 (OAI-compat + Ollama). URL change triggers debounced backend re-detection.

### Removed

- `LLMProviderLMStudio`, `LLMProviderOpenAI`, `LLMProviderTextGenWebUI` — replaced by `LLMProviderOAICompat`.
- `LLMGenerateTest` — test generation node superseded by `LLMGenerateAdvanced`.
- `LLMOptionsLMStudioTest` — test options node removed.

### Fixed

- `__init__.py` guarded with try/except to prevent pytest collection failures from relative imports.
- `defaultInput` deprecation warnings replaced with `forceInput` across all nodes.
- Textgen model dropdown auth retry now uses `get_admin_key("text_gen_webui")` so configured `admin_key` applies.

## [0.1.0] - 2026-03-13

### Added

- **Provider nodes** for three local LLM backends:
  - LM Studio (`LLM Provider: LM Studio`) with TTL-based model memory management
  - Ollama (`LLM Provider: Ollama`) with keep_alive-based model memory management
  - text-generation-webui (`LLM Provider: text-gen-webui`) with explicit model load/unload lifecycle
- **Generation nodes** for text generation:
  - Basic (`LLM Generate (Basic)`) — compact, inline params (temperature, max_tokens, seed)
  - Advanced (`LLM Generate (Advanced)`) — modular, accepts LLM_OPTIONS and LLM_META connections
- **Options nodes** for per-backend inference parameters:
  - Ollama Core Options — 7 common params with sentinel-value pattern
  - Ollama Extra Options — 10 advanced params with toggle pattern
  - LM Studio Options — 9 params with toggle pattern
  - text-gen-webui Options — 12 params with toggle pattern
- **Utility nodes:**
  - Preset Loader — loads .txt files from `presets/` directory
  - Load Text File — loads .txt files from ComfyUI's input folder
- **Adapter layer** with two adapters covering all backends:
  - Ollama Native adapter (`POST /api/chat`)
  - OpenAI-Compatible adapter (`POST /v1/chat/completions`) for LM Studio and text-gen-webui
- **YAML configuration** system with merge-on-load (`config.example.yaml` + `config.yaml`)
- **API key security** — keys resolved from config or environment variables, never stored in workflow JSON
- **Dynamic model dropdowns** via frontend JS querying running backends
- **PromptServer endpoints** for model lists (per-backend) and config reload
- **Graph introspection** for VRAM-aware unload deferral across chained generation nodes
- **Meta passthrough** (LLM_META) for chaining generation nodes without re-specifying provider/options
- **VALIDATE_INPUTS** on generation nodes for pre-execution checks
- **Structured error messages** with backend name, URL, HTTP status, and response body
