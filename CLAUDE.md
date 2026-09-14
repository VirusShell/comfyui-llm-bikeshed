# CLAUDE.md

Short agent guide for **comfyui-llm-bikeshed**. For architecture and decisions prefer `CODEBASE.md`, `docs/proposals/product-direction-and-scope.md`, and `docs/resolution_tracker.md`.

## Scope

ComfyUI custom nodes for **LLM text generation** only (no image/video/music/speech). One OpenAI-compatible adapter: `POST {url}/v1/chat/completions`.

| Path | Role |
|------|------|
| **LLM Provider: OAI Compatible** | Auto-detect at URL: LM Studio, Textgen, OpenAI, **llama.cpp** (`/v1`), generic OAI |
| **LLM Provider: Textgen** | Textgen-only URL + on-node `manage_model_memory` |

**Decision B:** llama.cpp servers that expose `/v1/chat/completions` (typically also `/health`, `/v1/models`) are **first-class on OAI Compatible**. A dedicated llama-server / process-manager node remains **deferred**. LM Studio and Textgen stay normal backends (OAI and/or dedicated Textgen provider).

Native **Ollama** is not in this pack. Do not put legal/personal names in artifacts — use **am_Vir** / **user** if a name is needed. Do not rename `LLM*` node class IDs.

## Durable pointers

- Lessons (non-obvious root causes / ComfyUI quirks): `docs/lessons-learned.md`
- External-claim provenance: `docs/research/provenance-and-reverification.md`
- Textgen HTTP/auth before path changes: `docs/research/textgen-lifecycle-verified.md`
- Cancel / interrupt: `docs/research/cancel-interrupt-status.md`
- Platform patterns: `docs/reference/comfyui-platform-findings.md`, `docs/reference/implementation-patterns.md`

## Packaging and quality

- Runtime deps: `pyyaml`, `requests` — mirrored in `pyproject.toml` and `requirements.txt`
- Dev: `pip install -e ".[dev]"` then `ruff check .` and `python -m pytest -q`
- Secrets: config/env only — never in widgets or workflow JSON

## Generate-node caching

`LLMGenerate` / `LLMGenerateAdvanced` return `float("NaN")` from `IS_CHANGED` **deliberately** so ComfyUI always re-runs LLM calls. See `CODEBASE.md`. Do not "fix" to a stable fingerprint without product intent.

## Hard stops (unless explicitly tasked)

- No force-push to shared remotes
- No V3 migration / Comfy-Action workflow CI kickoff
- No dedicated llama-server node
