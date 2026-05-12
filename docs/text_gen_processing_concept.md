# Text Generation & Processing — Node Design Concept

## comfyui-llm-bikeshed

**Date:** 2026-03-09
**Status:** Handoff-ready for Claude Code. Supersedes all prior concept docs and the original requirements.md.
**Companion doc:** resolution_tracker.md (source of truth for item status)

**Post–0.3.0 scope note:** Native **Ollama** is **not** implemented in this pack (D-3). Earlier text that lists Ollama as an in-pack backend or documents Ollama-specific nodes remains as **design history** unless a paragraph is explicitly refreshed; see `CHANGELOG.md` [0.3.0] and `docs/proposals/ollama-removal-plan.md`.

---

## Overview

This document defines the node architecture for the text generation and processing portion of comfyui-llm-bikeshed. It covers what node types are planned, what each one does, how they connect, and the reasoning behind the design direction.

Items confirmed through research are stated as such. Items that are assumptions or open questions are explicitly flagged and cross-referenced to the resolution tracker by ID (e.g., A-15, P-10).

Two existing Ollama-based node packs served as reference points during early design. They are influences, not blueprints.

- **comfyui-ollama-describer** — Compact, self-contained nodes. Strengths: low friction, quick to wire up. Weaknesses: locked to Ollama, hardcoded model list that triggers unwanted downloads, limited parameters, no extensibility.

- **comfyui-ollama** — Modular, split design (connectivity → options → generate). Strengths: full parameter access, flexible wiring, separation of concerns. Weaknesses: Ollama-only, very tall OllamaOptions node due to toggle pattern on every parameter, tied to the `ollama` Python SDK.

Our project aims for multi-provider support with both a compact "quick start" experience and a modular "full control" path.

---

## Scope Decisions (Firm)

**Supported local backends (in-pack, current):** LM Studio, text-generation-webui (oobabooga). Both support model memory management (TTL or explicit load/unload), which is critical for ComfyUI users sharing VRAM between LLM inference and Stable Diffusion. OpenAI Chat Completions uses the same OAI-compat adapter path. **Removed from pack (D-3):** native Ollama. (A-16)

**Dropped backends:** vLLM and standalone llama-server (llama.cpp direct). Neither has a model unload mechanism via API. Note that llama.cpp the *engine* is still supported — both LM Studio and text-gen-webui use it under the hood as an inference backend. Users who want llama.cpp inference use it through those tools. (A-16)

**Cloud providers:** Tabled for initial release. Other existing node packs already handle cloud LLM calls. Can be added later without breaking the local-focused architecture. (A-17)

---

## Node Categories

### Category 1: Provider / Connectivity Nodes

These nodes configure *where* LLM requests go. They output a connection (working name: `LLM_PROVIDER`) that generation nodes accept.

**All node names are placeholders.** Final naming will be workshopped once boundaries are settled.

Each Provider node handles:
- Connection settings (URL/host for the local backend)
- Model selection (dynamic dropdown from the running backend when available, with free-text fallback when offline — approach needs ComfyUI widget research, P-2, P-3)
- Model memory management (keep_alive, ttl, or explicit unload — per-backend)

#### Provider Nodes

| Working Name | Backend | API Used | Model Memory | Notes |
|-------------|---------|----------|-------------|-------|
| Provider (Ollama) | Ollama | Native (`/api/chat`, `/api/tags`) | `keep_alive` per-request. User-assignable, default "30s". | Full access to Ollama-specific features (mirostat, num_ctx, etc.) via native adapter. |
| Provider (LM Studio) | LM Studio | OAI-compat (`/v1/chat/completions`, `/v1/models`) | `ttl` per-request, in seconds. User-assignable, default 30. | Uses OAI-compat adapter. LM Studio's JIT loading + Auto-Evict complement the TTL. |
| Provider (text-gen-webui) | text-generation-webui | OAI-compat (`/v1/chat/completions`) + internal API (`/v1/internal/model/*`) | Explicit `POST /v1/internal/model/unload` after generation. See A-15 for chain behavior. | Model list via `GET /v1/internal/model/list`. Load via `POST /v1/internal/model/load`. Requires admin key (config/env, never on node — API-7). |

**Model memory management defaults (A-18):** All timeouts are user-assignable on the Provider node with short built-in defaults. Short defaults prioritize VRAM reclamation — in ComfyUI workflows, Stable Diffusion typically needs the GPU immediately after LLM text generation completes.

**Unload deferral in generation chains (A-15):**

When multiple generation nodes chain via `meta`, the model should stay loaded until the last node finishes. The timeout-based backends (Ollama, LM Studio) handle this naturally — the timer resets on each request within the chain. text-gen-webui is different because its unload is an explicit API call, not a timer.

Three approaches to research (assigned to Claude Code):
1. **Graph topology introspection (P-10):** Can a node's FUNCTION method determine if its `meta` output connects to another generation node downstream? If yes, only the last node fires unload. Cleanest approach but depends on ComfyUI platform capability. **Highest-priority research item.**
2. **Artificial delay:** text-gen-webui adapter uses a Python threading timer for unload, cancel-and-reset if another generation request arrives within the window. Fakes TTL behavior. Implementable without platform support.
3. **Manual user toggle:** "Unload after generation" boolean on Provider node. User sets to off for mid-chain nodes, on for the last. Simple but manual.

#### API Key Handling (Firm Decision)

- API keys are NEVER widget values on any node. Resolved server-side: `config.yaml` → environment variables → None.
- Provider nodes show a read-only status indicator ("Key: ✓ configured" / "Key: ✗ not found") for backends that need auth.
- Local providers generally don't require API keys. text-gen-webui's admin key for model management is handled the same way (config/env only).
- Zero API keys in serialized workflow JSON under any circumstances.

### Category 2: Generation Nodes

These nodes call the LLM and return text. **All names are placeholders.**

The current direction is two generation node variants — one compact, one modular — but whether this should be two nodes or one node with optional breakout connections is an open question (A-13, still exploring).

#### Basic Generation Node (working concept)

Compact, all-in-one. Everything needed for a standard text generation task on one node.

**Inputs (working list):**

| Input | Type | Required | Notes |
|-------|------|----------|-------|
| `provider` | LLM_PROVIDER | Yes | Connection from any Provider node |
| `system_prompt` | STRING | No | Multiline text field — always present for user editing |
| `preset` | (see below) | No | Populates system_prompt with shipped presets |
| `prompt` | STRING | Yes | Multiline text field |
| `temperature` | FLOAT | No | Inline, common default (TBD from cross-provider research) |
| `max_tokens` | INT | No | Inline, common default |
| `seed` | INT | No | Inline, -1 = random |

**Outputs (working list):**

| Output | Type | Notes |
|--------|------|-------|
| `text` | STRING | Generated text |
| `meta` | LLM_META | Provider + options passthrough for chaining. **Needs tooltip/hint on the node explaining what it carries.** |

**Preset mechanism (A-6, A-7, A-8):**

Presets should work like a file-loading pattern, not a JS widget interaction (which is unverified and has been a recurring implementation problem):

1. Preferred: Dropdown listing shipped preset `.txt` files from the node pack directory. Selecting one loads text into system_prompt field. Backend always reads the text field value, never the dropdown value.
2. Fallback: Separate Preset Loader node outputting STRING, connected to system_prompt input. Known-working pattern.
3. Either way: system_prompt text field always exists for direct editing. Empty is valid. Presets are convenience, not requirement.

Preset text content has not been authored yet — separate task (A-8).

#### Advanced Generation Node (working concept)

Modular, full control. No inline inference parameters. System prompt and user prompt have text fields (usable standalone) but also accept connections via `defaultInput`.

**Inputs (working list):**

| Input | Type | Required | Notes |
|-------|------|----------|-------|
| `provider` | LLM_PROVIDER | Yes | Connection from any Provider node |
| `system_prompt` | STRING | No | Multiline text field OR connection (defaultInput) |
| `prompt` | STRING | Yes | Multiline text field OR connection (defaultInput) |
| `options` | LLM_OPTIONS | No | Connection from Options node |
| `meta` | LLM_META | No | For chaining. **Needs tooltip/hint.** |

**Outputs (working list):**

| Output | Type | Notes |
|--------|------|-------|
| `text` | STRING | Generated text |
| `meta` | LLM_META | Provider + options passthrough |

The `defaultInput` behavior enables the existing workflow pattern: system prompts loaded from files via Load Text nodes, user prompts assembled by Text Concatenate chains.

**Meta precedence:** If `meta` connected and `provider` not → use meta's provider. If both connected → explicit `provider` wins. Same for options in meta vs explicit `options` input.

**Could this be a single node?** Worth exploring (A-13). If `defaultInput` on text fields keeps them visible and the inline parameters from the Basic node can be hidden/optional when an Options node is connected, one node might cover both use cases. Risk: cluttered node that serves neither audience well. Two nodes is the safe default, not a locked decision. Either way, both variants should work without an Options node attached (sensible model defaults).

### Category 3: Options Nodes

Options nodes configure *how* the LLM generates text. They output `LLM_OPTIONS` and connect to the Advanced generation node's `options` input.

#### Architecture — Open (A-1, A-2, A-3, A-4)

The right design depends on per-backend parameter research (API-4) that hasn't been done yet. Three approaches under consideration:

- **Per-provider:** Each backend gets its own Options node with exactly the parameters it supports. No chaining. Simple but duplicates common params.
- **Shared base + provider-specific:** One base Options node for widely-shared params, plus optional per-backend nodes for unique params. Needs a mechanism for combining both (chain, merge, or dual input slots).
- **Single node with toggles:** All parameters, per-parameter enable/disable. Disabled = model default, enabled = override. Explicit control but potentially very tall node.

**Blocking research needed before deciding (API-4):**
For each supported backend (Ollama native, LM Studio, text-gen-webui): what parameters does it accept, what names does it use, what happens with unknown parameters (ignore? reject? error?), and what are its defaults?

**Toggle widget reliability (P-9):** Do boolean toggles save/load correctly in ComfyUI? Needed before committing to the toggle approach.

#### Parameters Confirmed as Provider-Specific

- `keep_alive` (Ollama) / `ttl` (LM Studio) — On Provider nodes, not Options. Connection/server concern.
- `mirostat`, `mirostat_tau`, `mirostat_eta` — Ollama-native only.
- `num_ctx` — Ollama-native. Other backends set context length at server configuration level.
- `tfs_z`, `repeat_last_n` — Ollama-native.

#### Parameters Likely Cross-Provider (Needs Confirmation)

- `temperature` — Likely universal.
- `max_tokens` / `num_predict` — Universal concept, name varies. Adapter maps.
- `top_p` — Widely supported.
- `top_k` — Most backends except OpenAI (tabled, but relevant for future cloud support).
- `seed` — Ollama, LM Studio. Not all providers.
- `stop` sequences — Likely universal. Format varies.
- `frequency_penalty` / `presence_penalty` — OAI-compat backends. Not Ollama native.
- `repeat_penalty` — Ollama, most local backends.

**None of these are committed to any Options node design until per-backend research is complete.**

---

## Structured Output Support

**Status: Needs research. Not designed around.** (A-12)

Pulled from the generation node designs until we understand how it works across providers, what the practical use cases are in ComfyUI workflows, and how the mechanisms compare (native JSON mode, schema-in-prompt, Ollama's format parameter, Pydantic schema input as in comfyui-ollama-describer).

---

## Adapter Layer (Internal, Not User-Facing)

Sits between generation nodes and HTTP calls. Selected by the Provider node's configuration.

Each adapter:
- Translates a generic generation call into the backend's API format
- Applies its parameter allowlist (drops unsupported params, logs at info level — A-10)
- Maps parameter names where needed (max_tokens → num_predict for Ollama, etc.)
- Handles response extraction (path to text content differs per backend)
- Reports errors with backend name, URL, HTTP status, and response body

**Adapters:**

| Adapter | Used By | API Format |
|---------|---------|------------|
| Ollama Native | Provider (Ollama) | `POST {url}/api/chat` |
| OpenAI-Compatible | Provider (LM Studio), Provider (text-gen-webui) | `POST {url}/v1/chat/completions` |

The OAI-compat adapter needs per-backend awareness for parameter allowlists, since text-gen-webui and LM Studio may accept different extended parameters beyond the OpenAI standard.

All adapters use `requests` (synchronous HTTP). PromptServer endpoints for model lists use `asyncio.to_thread()` to call `requests` without blocking ComfyUI's event loop. (I-1, confirmed)

---

## What This Doesn't Cover (Yet)

- **Image Describe nodes** — Same generation node pattern with `IMAGE` input. Same Provider and Options nodes. Future scope.
- **Chat nodes** — Conversation history input/output. Scope (predetermined chains vs interactive session state) is open (A-5).
- **User-created preset management** — Users already solve this with Load Text nodes. Dedicated system is a future enhancement.
- **Batch processing** — Image Describe will need batch handling. Text gen is one-in-one-out.
- **Cloud providers** — Tabled. Can be added later (A-17).

---

## Priority Research for Claude Code

Ordered by impact on design decisions:

1. **P-10: Graph topology introspection.** Can a node's FUNCTION method know what its outputs connect to? Unlocks clean unload deferral (A-15) and potentially other chain-aware behavior. Highest value.

2. **API-4: Per-backend parameter mapping.** For Ollama, LM Studio, and text-gen-webui: accepted parameters, names, handling of unknowns, defaults. Unblocks Options node architecture (A-1, A-2, A-3).

3. **P-9: Toggle widget reliability.** Do boolean toggles save/load correctly? Needed before committing to enable/disable toggle pattern for Options.

4. **P-2 / P-3: Dynamic COMBO behavior.** What happens to saved model names when backend is offline? Can COMBO fall back to text input reliably?

5. **A-6: Preset file-loading mechanism.** Can a dropdown of shipped .txt files load text into an adjacent STRING widget reliably on selection? Save/load behavior?

---

## Design Principles

1. **The LLM node does one job.** Generate text from a prompt. Text manipulation before and after is handled by existing community nodes.

2. **Configuration flows through connections, not hidden state.** Everything that affects output is visible in the graph.

3. **API keys are invisible to the graph.** Config file or environment variables. Never serialized.

4. **Adapters are the translation layer.** Generation nodes don't know about API formats. Adapters don't know about ComfyUI nodes.

5. **Sensible defaults everywhere.** Both node variants should work with minimal configuration. It's up to the user and their needs which to use.

6. **No forced model downloads.** Dynamic model lists show what's available. Fallback to free-text when offline.

7. **VRAM is shared.** ComfyUI workflows use the same GPU for diffusion and LLM inference. Model memory management is not optional — it's a core design requirement, not an afterthought.

8. **Don't lock in what isn't confirmed.** Unverified assumptions are flagged, not presented as decisions.

---

## User's Existing Workflow (Context for Claude Code)

The user has a Flux prompt optimization workflow that demonstrates the real-world usage pattern these nodes need to support:

- Single user prompt → LLM processes it into two different formats (CLIP-L tags and T5 natural language) via the same model with different system prompts and token limits
- System prompts loaded from external `.txt` files via comfyui-custom-scripts Load Text nodes pointed at a directory
- Task-specific instructions prepended via Text Concatenate nodes
- Post-processing with general-purpose text nodes (CR Text Replace, TextBoxConcatenate, Add LoRA)
- Structured prompt archive built from concatenation nodes and saved with date-based file organization

Key takeaway: The user is not looking for a monolithic LLM node. They build workflows where the LLM is one focused step in a chain, with text manipulation handled by other nodes before and after. The project's value is making the LLM call cleaner and more flexible (multi-provider, proper options, memory management), not absorbing all text processing.
