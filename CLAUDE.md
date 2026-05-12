# CLAUDE.md

> **Lessons Learned (MANDATORY):** After any of these events, add an entry to `docs/lessons-learned.md`:
> - A bug fix that revealed a non-obvious root cause
> - A test passed locally but failed in ComfyUI's runtime environment
> - A dependency, import, or packaging issue was discovered
> - A design assumption turned out to be wrong
> - A workaround was needed for ComfyUI behavior not covered in docs
>
> Each entry needs: date, severity, what happened, root cause, fix, and how to prevent it next time. If unsure whether something qualifies, add it — too many entries is better than a missing one.

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ComfyUI custom node pack that connects workflows to **Ollama**, **LM Studio**, **Textgen** (text-generation-webui), and optional **OpenAI** Chat Completions (keys via config/env only). Scope is strictly LLM text generation: no image/video/music/speech generation. Additional cloud APIs beyond OpenAI core chat remain out of scope until explicitly added.

**Current status:** Pre-implementation (design phase). Authoritative docs:
- `docs/text_gen_processing_concept.md` — node architecture and design decisions
- `docs/resolution_tracker.md` — source of truth for open questions, assumptions, and confirmed decisions
- `docs/proposals/product-direction-and-scope.md` — **non-authoritative** roadmap signals (Textgen-first, lifecycle rethink, planned Ollama removal as docs-stage intent with code removal follow-up, llama.cpp deferred). Reconcile older tracker rows (e.g. A-16) when implementation proceeds.

Old docs (`docs/old/CONCEPT.md`, `docs/old/RESEARCH_BRIEF.md`) are superseded — do not reference them for current decisions.

## ComfyUI Custom Node Reference

Comprehensive research on ComfyUI custom node development standards is at `D:\ai\tmp\comfyui-custom-nodes-research\`. Consult these files for implementation-level detail:

| File | Covers |
|------|--------|
| `01-overview.md` | Architecture, node categories (server-only, client-only, connected) |
| `02-getting-started.md` | Scaffolding, registration, `NODE_CLASS_MAPPINGS`, first node walkthrough |
| `03-backend-properties.md` | All class properties (`INPUT_TYPES`, `RETURN_TYPES`, `IS_CHANGED`, `VALIDATE_INPUTS`, etc.) |
| `04-backend-datatypes.md` | Primitive types, tensor shapes (IMAGE `[B,H,W,C]`, LATENT, MASK), custom types |
| `05-backend-advanced.md` | Lazy evaluation, node expansion, data lists, hidden inputs, flexible inputs, node replacement |
| `06-javascript-extensions.md` | Frontend hooks, extension registration, UI APIs (settings, sidebar, toast, dialog) |
| `07-v3-migration.md` | V3 schema API (`io.ComfyNode`, `define_schema()`), V1→V3 property mapping |
| `08-node-docs-templates-subgraphs.md` | Node help pages, workflow templates, subgraph blueprints |
| `09-registry-publishing.md` | Registry, `pyproject.toml`, publishing workflow, security prohibitions |
| `10-snippets-examples.md` | Image/mask/noise handling patterns, context menu patterns |
| `11-i18n-and-context-menu-migration.md` | Localization, deprecated prototype hijacking → official hooks |
| `LEDGER.md` | Master index with coverage tracking and confidence ratings |

Additional verified patterns in project memory: `comfyui-node-standards.md` (widget system, rendering pipeline, layout constants, anti-patterns).

## Architecture

### Supported Backends (A-16, firm)

| Backend | API | Model Memory | Notes |
|---------|-----|-------------|-------|
| Ollama | Native (`/api/chat`, `/api/tags`) | `keep_alive` per-request, default "30s" | Full access to Ollama-specific params via native adapter |
| LM Studio | OAI-compat (`/v1/chat/completions`, `/v1/models`) | `ttl` per-request, default 30s | JIT loading + Auto-Evict complement TTL |
| Textgen (text-generation-webui) | OAI-compat + internal API (`/v1/internal/model/*`) | Explicit unload via API | Requires admin key (config/env only) |
| OpenAI API | OAI-compat (`/v1/chat/completions`, `/v1/models`) | No local VRAM lifecycle | Core sampling params only; keys config/env only |

**Dropped:** vLLM and standalone llama-server — no model unload API. llama.cpp the engine is still supported indirectly through LM Studio and Textgen.

**Other cloud providers (A-17):** Beyond OpenAI core chat, tabled until explicitly scoped.

### Adapter Pattern

Two adapters cover all supported backends:
- **Ollama Native** — `POST {url}/api/chat`
- **OpenAI-Compatible** — `POST {url}/v1/chat/completions` (OpenAI API, LM Studio, Textgen)

All API calls use `requests` (synchronous HTTP). No provider SDKs (`openai`, `anthropic`, `google-genai`). PromptServer endpoints for model lists use `asyncio.to_thread()` to avoid blocking ComfyUI's event loop.

Each adapter handles: parameter allowlist filtering (drops unsupported params, logs at info level), parameter name mapping (e.g., `max_tokens` → `num_predict` for Ollama), response extraction, and error reporting with backend name, URL, HTTP status, and response body.

### Node Design

**Provider nodes (A-14):** Separate node per backend (not a single dropdown node). Each has static widgets for its provider. All output the same `LLM_PROVIDER` type.

**Generation nodes (A-13, still exploring):** Two variants under consideration:
- **Basic** — compact, all-in-one with inline params (temperature, max_tokens, seed) and optional preset dropdown
- **Advanced** — modular, no inline params; accepts `LLM_OPTIONS` and `LLM_META` connections; text fields support `defaultInput`

Whether these are two nodes or one node with optional breakout connections is not yet decided.

**Options nodes (A-1, A-2, A-3 — open):** Architecture blocked on per-backend parameter research (API-4). Three approaches under consideration: per-provider nodes, shared base + provider-specific, or single node with toggles.

**Meta passthrough:** Generation nodes output `LLM_META` carrying provider + options for chaining without re-specifying config on each node.

### VRAM is Shared (Core Requirement)

ComfyUI workflows share the same GPU for diffusion and LLM inference. Model memory management is not optional — short TTL/keep_alive defaults prioritize VRAM reclamation so Stable Diffusion can use the GPU immediately after LLM generation completes. Chain-aware unload deferral for text-gen-webui is an open research item (A-15, P-10).

## Key Design Constraints

- **API keys must never be stored in workflow JSON.** ComfyUI serializes widget values — keys would leak in shared workflows. Resolution order: `config.yaml` → environment variables → None (local backends). Provider nodes show a read-only status indicator, not an editable key field.
- **System prompt is a first-class visible input** on every generation node. Preset dropdowns populate the field but it's always directly editable.
- **Options node is optional** — disconnect it and the model uses its own defaults.
- **Unsupported parameters** sent to a backend are silently dropped (logged at info level), not errors.
- **Target V1 node spec** — V3 is the future direction but still in development. Keep node logic cleanly separated from V1 boilerplate so migration is mechanical later.
- **No forced model downloads.** Dynamic model lists show what's available; free-text fallback when backend is offline.

## Dependencies (Intentionally Minimal)

Runtime: `requests`, `pyyaml>=6.0`, `pillow>=9.0.0`, `numpy>=1.24.0`. Pillow and numpy are already in ComfyUI. Explicitly excluded: torch, transformers, opencv, aiohttp, any provider SDK.

## Configuration

YAML config file (`config.yaml`, gitignored) for API keys, host overrides, and defaults. `config.example.yaml` ships with the repo. Frontend JS in `js/` directory (`WEB_DIRECTORY = "./js"`) for dynamic model dropdowns querying running backends.

## Open Questions & Research

Many design decisions are unresolved. Before making assumptions, check `docs/resolution_tracker.md` — it tracks the status of every decision (Confirmed, Decided, Assumed, Unresolved, Contaminated).

**Priority research items for Claude Code** (from concept doc):
1. **P-10:** Graph topology introspection — can a node's FUNCTION method know what its outputs connect to? (Highest impact)
2. **API-4:** Per-backend parameter mapping — accepted params, names, handling of unknowns, defaults
3. **P-9:** Toggle widget save/load reliability
4. **P-2/P-3:** Dynamic COMBO behavior when backend is offline
5. **A-6:** Preset file-loading mechanism reliability

## Future Scope (Not in Initial Release)

- Image Describe nodes (same generation pattern with `IMAGE` input)
- Chat nodes (conversation history — scope TBD per A-5)
- Structured Output nodes (needs per-provider research per A-12)
- Additional cloud providers beyond OpenAI core chat (Anthropic, Gemini, OpenRouter, etc.)
- User-created preset management
