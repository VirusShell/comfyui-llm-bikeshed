# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **OpenAI API** — `LLM Provider: OpenAI` and `LLM Options: OpenAI` for non-streaming Chat Completions (`POST /v1/chat/completions`) with core sampling allowlist; model list via `GET /v1/models`; API key from `config.yaml` / `LLM_BIKESHED_OPENAI_API_KEY` only.

### Changed

- **Display names:** text-gen-webui provider/options nodes show as **Textgen** in the UI (Python class names unchanged).

### Fixed

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
