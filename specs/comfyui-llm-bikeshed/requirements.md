# Requirements: comfyui-llm-bikeshed

**Version:** v0.1.0
**Date:** 2026-03-10
**Status:** Awaiting approval
**Resolution tracker:** `docs/resolution_tracker.md`
**Design doc:** `docs/text_gen_processing_concept.md`
**Design review:** `docs/design_review_update_2026-03-10.md`

---

## Goal

Provide ComfyUI custom nodes that connect workflows to local LLM backends (LM Studio, text-generation-webui, Ollama) for text generation, with VRAM-aware model memory management, per-provider configuration, and both compact and modular node variants. Replace existing LLM nodes in prompt optimization workflows with cleaner wiring and equivalent or better results.

---

## User Stories

### Provider Configuration

#### US-1: Connect to LM Studio
**As a** ComfyUI user running LM Studio locally
**I want to** drop a Provider node, pick my model from a dropdown, and connect it to a generation node
**So that** I can generate text without manual URL/model string entry

**Acceptance Criteria:**
- [ ] AC-1.1: LM Studio Provider node exists with `url` field (default `http://localhost:1234`)
- [ ] AC-1.2: Model COMBO dropdown populates from `GET {url}/v1/models` via PromptServer endpoint
- [ ] AC-1.3: Refresh button re-queries model list on click
- [ ] AC-1.4: If LM Studio is offline, dropdown shows fallback state; saved model name persists
- [ ] AC-1.5: `ttl` field (INT, seconds, default 30) controls model idle timeout per-request
- [ ] AC-1.6: Node outputs `LLM_PROVIDER` type connectable to any generation node
- [ ] AC-1.7: STRING `model_fallback` input with `defaultInput: True` available as manual model name override
- [ ] AC-1.8: If `model_fallback` has a non-empty value, it overrides the COMBO dropdown selection for model name
- [ ] AC-1.9: PromptServer endpoint attempts request without auth first; includes key only if configured; returns empty list on 401/403 with info-level log

#### US-2: Connect to text-generation-webui
**As a** ComfyUI user running text-generation-webui
**I want to** connect to my backend with proper auth handling
**So that** I can use text-gen-webui's model management features

**Acceptance Criteria:**
- [ ] AC-2.1: text-gen-webui Provider node exists with `url` field (default `http://localhost:5000`)
- [ ] AC-2.2: Model COMBO dropdown populates from `GET {url}/v1/internal/model/list` (uses admin key if configured)
- [ ] AC-2.3: Refresh button re-queries model list
- [ ] AC-2.4: API key resolved from config.yaml → env var → None (never on node widget) [Traces: API-7]
- [ ] AC-2.5: Config supports both `api_key` (generation) and `admin_key` (model management) [Traces: API-7]
- [ ] AC-2.6: If only one key configured, it's used for both purposes
- [ ] AC-2.7: Node outputs `LLM_PROVIDER` type
- [ ] AC-2.8: STRING `model_fallback` input with `defaultInput: True` as manual model name override
- [ ] AC-2.9: If `model_fallback` has a non-empty value, it overrides the COMBO dropdown selection
- [ ] AC-2.10: PromptServer endpoint attempts request without auth first; includes key only if configured; returns empty list on 401/403 with info-level log

#### US-3: Connect to Ollama
**As a** ComfyUI user running Ollama
**I want to** connect to Ollama and control model memory
**So that** I can free VRAM for Stable Diffusion after LLM generation

**Acceptance Criteria:**
- [ ] AC-3.1: Ollama Provider node exists with `url` field (default `http://localhost:11434`)
- [ ] AC-3.2: Model COMBO dropdown populates from `GET {url}/api/tags` via PromptServer endpoint
- [ ] AC-3.3: Refresh button re-queries model list
- [ ] AC-3.4: `keep_alive` field (STRING, default `"30s"`) sent as top-level request param
- [ ] AC-3.5: Node outputs `LLM_PROVIDER` type
- [ ] AC-3.6: STRING `model_fallback` input with `defaultInput: True` as manual model name override
- [ ] AC-3.7: If `model_fallback` has a non-empty value, it overrides the COMBO dropdown selection

#### US-4: API Key Security
**As a** user who shares workflows
**I want** API keys to never appear in exported workflow JSON
**So that** my credentials are not leaked

**Acceptance Criteria:**
- [ ] AC-4.1: No Provider node has an API key widget
- [ ] AC-4.2: API key resolution chain: config.yaml → env var (`LLM_BIKESHED_{PROVIDER}_API_KEY`) → None
- [ ] AC-4.3: Exporting any workflow containing Provider nodes produces JSON with zero API key values [Traces: S-3]
- [ ] AC-4.4: Provider node shows read-only status indicator ("Key: configured" / "Key: not found") for backends requiring auth

### Text Generation

#### US-5: Quick Text Generation (Basic Node)
**As a** newcomer
**I want to** wire a provider to a single compact node, type a prompt, and get text back
**So that** I can start generating without understanding the full modular system

**Acceptance Criteria:**
- [ ] AC-5.1: Basic Generation node exists with inline `temperature` (FLOAT, default 0.7, range 0.0-2.0), `max_tokens` (INT, default 1024), `seed` (INT, default -1 = random). All are user-editable widgets. Adapter handles name mapping (e.g., `max_tokens` → `num_predict` for Ollama).
- [ ] AC-5.2: `provider` input (LLM_PROVIDER, required)
- [ ] AC-5.3: `prompt` input (STRING, multiline, required)
- [ ] AC-5.4: `system_prompt` input (STRING, multiline, optional, always visible and editable)
- [ ] AC-5.5: Outputs `text` (STRING) and `meta` (LLM_META)
- [ ] AC-5.6: Works without an Options node — inline params are sufficient
- [ ] AC-5.7: `IS_CHANGED` returns `float("NaN")` (LLM calls are non-deterministic) [Traces: A-11]
- [ ] AC-5.8: Hidden inputs declared: `"prompt": "PROMPT"`, `"unique_id": "UNIQUE_ID"` for graph introspection [Traces: P-10]

#### US-6: Modular Text Generation (Advanced Node)
**As a** power user
**I want** a generation node with no inline params that accepts everything via connections
**So that** I can build complex multi-step LLM chains with full control

**Acceptance Criteria:**
- [ ] AC-6.1: Advanced Generation node exists with NO inline inference params
- [ ] AC-6.2: `provider` input (LLM_PROVIDER, required) — OR inherited from `meta`
- [ ] AC-6.3: `prompt` input (STRING, multiline, required, `defaultInput: True` so it accepts connections)
- [ ] AC-6.4: `system_prompt` input (STRING, multiline, optional, `defaultInput: True`)
- [ ] AC-6.5: `options` input (LLM_OPTIONS, optional)
- [ ] AC-6.6: `meta` input (LLM_META, optional) for chaining
- [ ] AC-6.7: Outputs `text` (STRING) and `meta` (LLM_META)
- [ ] AC-6.8: Meta precedence: explicit `provider` input wins over meta's provider; explicit `options` input wins over meta's options [Traces: concept doc]
- [ ] AC-6.9: Works without Options node — model uses its own defaults
- [ ] AC-6.10: `IS_CHANGED` returns `float("NaN")` [Traces: A-11]
- [ ] AC-6.11: Hidden inputs declared: `"prompt": "PROMPT"`, `"unique_id": "UNIQUE_ID"` for graph introspection [Traces: P-10]

#### US-7: Chain Multiple Generations
**As a** user with a Flux prompt optimization workflow
**I want to** chain two generation nodes (e.g., CLIP-L tags + T5 natural language) from the same model
**So that** the model stays loaded across the chain and unloads only after the last node

**Acceptance Criteria:**
- [ ] AC-7.1: `meta` output carries provider + options for downstream generation nodes
- [ ] AC-7.2: Generation node uses PROMPT hidden input to reverse-index downstream connections [Traces: P-10, A-15]
- [ ] AC-7.3: If meta output connects to another generation node, skip unload/set long keep_alive
- [ ] AC-7.4: If meta output has no downstream generation node, fire unload (text-gen-webui) or use short keep_alive/ttl (Ollama/LM Studio)
- [ ] AC-7.5: Hidden inputs declared: `"prompt": "PROMPT"`, `"unique_id": "UNIQUE_ID"`

### Options Configuration

#### US-8: Configure Ollama Parameters
**As a** user wanting fine control over Ollama inference
**I want** Options nodes with Ollama parameters, split into common and advanced
**So that** common params are compact and advanced tuning is available when needed

**Acceptance Criteria:**
- [ ] AC-8.1: **Ollama Core Options** node exists with sentinel-value pattern (NO toggles). Sentinel value (e.g., -1) means "use model default" — adapter excludes param from request. [Traces: A-1, design review §3]
- [ ] AC-8.2: Core parameters: `temperature` (FLOAT, sentinel -1), `top_k` (INT, sentinel -1), `top_p` (FLOAT, sentinel -1), `seed` (INT, sentinel -1 = random), `num_predict` (INT, sentinel -1 = unlimited), `num_ctx` (INT, sentinel -1 = model default 2048), `stop` (STRING, sentinel empty)
- [ ] AC-8.3: Core node outputs `LLM_OPTIONS` type
- [ ] AC-8.4: Core node has `options_in` (LLM_OPTIONS, optional) input for chaining from Extra node
- [ ] AC-8.5: **Ollama Extra Options** node exists with BOOLEAN toggle per parameter. Toggle OFF = excluded (model default). Toggle ON = value sent. `label_on`/`label_off` set to "ON"/"OFF". [Traces: A-3]
- [ ] AC-8.6: Extra parameters: `mirostat` (INT COMBO: 0/1/2), `mirostat_eta` (FLOAT, default 0.1), `mirostat_tau` (FLOAT, default 5.0), `repeat_penalty` (FLOAT, default 1.1), `repeat_last_n` (INT, default 64), `frequency_penalty` (FLOAT, default 0.0), `presence_penalty` (FLOAT, default 0.0), `tfs_z` (FLOAT, default 1.0), `typical_p` (FLOAT, default 1.0), `min_p` (FLOAT, default 0.0)
- [ ] AC-8.7: Extra node outputs `LLM_OPTIONS` type and has `options_in` (LLM_OPTIONS, optional) input
- [ ] AC-8.8: Chain: `[Extra] → options_in → [Core] → options → [Generation Node]`. Core values override Extra for any key collision.
- [ ] AC-8.9: Extra node is entirely optional — Core alone is sufficient

#### US-9: Configure LM Studio Parameters
**As a** user wanting control over LM Studio inference
**I want** an Options node with LM Studio's supported parameters

**Acceptance Criteria:**
- [ ] AC-9.1: LM Studio Options node with BOOLEAN toggle per parameter [Traces: A-1, A-3]
- [ ] AC-9.2: Parameters include: temperature, top_p, max_tokens, seed, stop, top_k, repeat_penalty, presence_penalty, frequency_penalty
- [ ] AC-9.3: Toggle OFF = param excluded from API call (model default). Toggle ON = param value sent. `label_on`/`label_off`: "ON"/"OFF".
- [ ] AC-9.4: Outputs `LLM_OPTIONS` type
- [ ] AC-9.5: Single node (9 params × 2 widgets = 18 widgets). Split only if too tall in UI during implementation.

#### US-10: Configure text-gen-webui Parameters
**As a** user wanting control over text-gen-webui inference
**I want** an Options node with text-gen-webui's supported parameters

**Acceptance Criteria:**
- [ ] AC-10.1: text-gen-webui Options node with BOOLEAN toggle per parameter [Traces: A-1, A-3]
- [ ] AC-10.2: Parameters include: temperature, top_p, max_tokens, seed, stop, top_k, min_p, repeat_penalty, presence_penalty, frequency_penalty, typical_p, tfs
- [ ] AC-10.3: Toggle OFF = param excluded (model default). Toggle ON = value sent. `label_on`/`label_off`: "ON"/"OFF".
- [ ] AC-10.4: Outputs `LLM_OPTIONS` type
- [ ] AC-10.5: Single node (12 params × 2 widgets = 24 widgets). May split into Core/Extra post-implementation if too tall — same pattern as Ollama split.

### Presets & Text Loading

#### US-11: Load System Prompt Presets
**As a** user
**I want** a Preset Loader node that lists .txt files from a presets directory
**So that** I can quickly select shipped system prompts and connect them to generation nodes

**Acceptance Criteria:**
- [ ] AC-11.1: Preset Loader node exists with COMBO widget listing `.txt` filenames from `presets/` directory [Traces: A-6, A-7]
- [ ] AC-11.2: Output is STRING containing the file's text content
- [ ] AC-11.3: Connect output to any generation node's `system_prompt` input
- [ ] AC-11.4: `presets/` directory ships with a README placeholder (no authored presets in v0.1.0) [Traces: A-8]
- [ ] AC-11.5: If `presets/` is empty or has no .txt files, COMBO shows a fallback entry

#### US-14: Load User Text Files
**As a** user
**I want** a Load Text File node that reads .txt files from ComfyUI's input folder
**So that** I can load my own system prompts without needing an external node pack

**Acceptance Criteria:**
- [ ] AC-14.1: Load Text File node exists with COMBO widget listing `.txt` files from a configurable directory (default: ComfyUI `input/` folder) [Traces: design review §4]
- [ ] AC-14.2: Output is STRING containing the file's text content
- [ ] AC-14.3: Connect output to any STRING input (system_prompt, prompt, etc.)
- [ ] AC-14.4: Refresh picks up new files (ComfyUI's `r` hotkey triggers `INPUT_TYPES` re-call)
- [ ] AC-14.5: Minimal node — COMBO of filenames, one STRING output. No editing, saving, or subdirectory browsing.

### Configuration System

#### US-12: YAML Configuration
**As a** user
**I want** a config.yaml file for API keys, URLs, and defaults
**So that** I can configure the node pack once without touching node widgets

**Acceptance Criteria:**
- [ ] AC-12.1: `config.example.yaml` ships with documented defaults for all three providers
- [ ] AC-12.2: User copies to `config.yaml` (gitignored) and overrides values
- [ ] AC-12.3: Merge-on-load: `config.example.yaml` deep-merged with `config.yaml`; user values win [Traces: I-7]
- [ ] AC-12.4: New keys in `config.example.yaml` appear with defaults after update; user keys preserved
- [ ] AC-12.5: Neither file modified on disk at runtime
- [ ] AC-12.6: Config cached on module load; reload via `/llm-bikeshed/reload-config` endpoint [Traces: P-5]
- [ ] AC-12.7: `yaml.safe_load()` used (no arbitrary code execution)

### Frontend

#### US-13: Dynamic Model Dropdowns
**As a** user
**I want** model dropdowns that query running backends and update automatically
**So that** I see available models without manual entry

**Acceptance Criteria:**
- [ ] AC-13.1: Frontend JS extension registered as `llm-bikeshed.model-dropdown`
- [ ] AC-13.2: `nodeCreated` hook populates model COMBO widget from PromptServer endpoint
- [ ] AC-13.3: Each Provider node type queries its backend's model list endpoint
- [ ] AC-13.4: Refresh button on each Provider node re-fetches models
- [ ] AC-13.5: Saved model name persists in `widgets_values` across save/load regardless of backend state
- [ ] AC-13.6: JS files served from `./js` directory [Traces: I-6]

---

## Functional Requirements

| ID | Requirement | Priority | Traces To | Acceptance Criteria |
|----|-------------|----------|-----------|---------------------|
| FR-1 | Three Provider nodes (LM Studio, text-gen-webui, Ollama), each outputting LLM_PROVIDER | High | A-14, S-2 | AC-1.6, AC-2.7, AC-3.5 |
| FR-2 | Basic Generation node with inline params (temperature, max_tokens, seed) | High | A-13 | AC-5.1 through AC-5.8 |
| FR-3 | Advanced Generation node with connection-only config | High | A-13 | AC-6.1 through AC-6.11 |
| FR-4 | Per-provider Options nodes. Ollama: Core (sentinel values, 7 params) + Extra (toggles, 10 params). LM Studio: single node with toggles (9 params). text-gen-webui: single node with toggles (12 params, may split later). | High | A-1, A-3, design review §3 | AC-8.x, AC-9.x, AC-10.x |
| FR-5 | Ollama Native adapter (`POST {url}/api/chat`) | High | -- | Translates generic call to Ollama format; maps param names (max_tokens→num_predict); params go in `options` object |
| FR-6 | OpenAI-Compatible adapter (`POST {url}/v1/chat/completions`) | High | -- | Serves LM Studio and text-gen-webui; per-backend param allowlists |
| FR-7 | Adapter allowlist filtering — unsupported params silently dropped, info-level log | High | A-10 | Param not in allowlist → excluded from request, logged at info level |
| FR-8 | Meta passthrough (LLM_META carries provider + options) | High | -- | AC-7.1, AC-6.8 |
| FR-9 | VRAM-aware unload deferral via graph introspection | High | A-15, P-10 | AC-7.2 through AC-7.5 |
| FR-10 | Config system with merge-on-load and API key resolution | High | I-7 | AC-12.1 through AC-12.7 |
| FR-11 | Dynamic model dropdowns via frontend JS | High | P-2, P-3 | AC-13.1 through AC-13.6 |
| FR-12 | Preset Loader node (COMBO of .txt files from `presets/` → STRING) | Medium | A-6 | AC-11.1 through AC-11.5 |
| FR-13 | PromptServer endpoints for model lists (one per backend). Attempt without auth first, include key only if configured, return empty list on 401/403 with info log. | High | design review §5 | AC-1.9, AC-2.10 |
| FR-14 | PromptServer endpoint for config reload | Medium | P-5 | AC-12.6 |
| FR-15 | VALIDATE_INPUTS on generation nodes for pre-execution checks | Medium | I-3 | URL format valid, provider config present |
| FR-16 | text-gen-webui explicit model unload after generation (last node in chain only) | High | A-15, API-6 | `POST {url}/v1/internal/model/unload` called only when no downstream gen node |
| FR-17 | System prompt as first-class visible input on every generation node | High | -- | AC-5.4, AC-6.4 |
| FR-18 | `stream: false` on all API calls | High | -- | No streaming in v0.1.0 |
| FR-19 | text-gen-webui adapter checks model status via `GET /v1/internal/model/info` and loads selected model via `POST /v1/internal/model/load` before generation if correct model not already loaded. Uses admin key from config if available. | High | design review §1 | Full lifecycle: check → load → generate → unload |
| FR-20 | Load Text File utility node. COMBO lists `.txt` files from configurable directory (default: ComfyUI `input/` folder). Output is STRING. | Medium | design review §4 | AC-14.1 through AC-14.5 |
| FR-21 | Model selection priority: STRING `model_fallback` overrides COMBO dropdown on all Provider nodes | High | design review §2 | AC-1.8, AC-2.9, AC-3.7 |

---

## Non-Functional Requirements

| ID | Requirement | Metric | Target |
|----|-------------|--------|--------|
| NFR-1 | HTTP timeout | Default seconds | 120s, configurable per-provider in config.yaml [Traces: I-5] |
| NFR-2 | Error reporting | Exception detail | Backend name, URL, HTTP status, response body in error message [Traces: I-4] |
| NFR-3 | No retry logic | Failure behavior | Fail immediately on HTTP error; raise exception to halt workflow [Traces: I-4] |
| NFR-4 | Dependency footprint | Runtime deps | `pyyaml>=6.0`, `requests>=2.28.0` only. No provider SDKs. [Traces: I-1] |
| NFR-5 | Security — no eval/exec | Code safety | Zero use of `eval()`, `exec()`, or `subprocess` for pip |
| NFR-6 | Security — safe YAML | Parsing safety | `yaml.safe_load()` only, never `yaml.load()` |
| NFR-7 | ComfyUI compatibility | Target spec | V1 node spec. V3 is future migration. |
| NFR-8 | Python version | Minimum | Python 3.10+ (matches ComfyUI requirement) |
| NFR-9 | Logging | Framework | Python `logging` module, logger name `llm-bikeshed` |
| NFR-10 | Toast notifications | Non-fatal warnings | JS toast API for warnings (e.g., "Parameter X unsupported by Y, ignored") [Traces: P-4] |

---

## Design Departures

| Area | Research Recommendation | Actual Decision | Rationale |
|------|------------------------|-----------------|-----------|
| HTTP library | CLAUDE.md specified `aiohttp>=3.8.0` | `requests>=2.28.0` (sync) | ComfyUI nodes run synchronously. `requests` is simpler and matches ecosystem patterns. PromptServer endpoints use `asyncio.to_thread()` bridge. [I-1] |
| LM Studio TTL default | LM Studio app default is 60 minutes | Our default is 30 seconds | Short default prioritizes VRAM reclamation for shared GPU workflows. User-configurable. [A-18] |
| Dependency list | Original: aiohttp, pyyaml, pillow, numpy | Actual: pyyaml, requests only | Pillow and numpy are ComfyUI deps (not ours). aiohttp replaced by requests. |
| Ollama Options architecture | Single Options node with all toggles | Core/Extra split | 17 params with toggles = 34 widgets (anti-pattern). Core uses sentinel values for 7 common params (compact). Extra uses toggles for 10 advanced params (optional). [design review §3] |

---

## Error Handling Summary

| Situation | Mechanism | Detail |
|-----------|-----------|--------|
| API call fails (HTTP error) | Raise exception in FUNCTION | Message includes: backend name, URL, HTTP status, response body. Workflow halts, red outline on node. |
| Network timeout | Raise exception | Default 120s, configurable per-provider. Message identifies provider and URL. |
| Invalid config (pre-execution) | VALIDATE_INPUTS | Check URL format valid, required provider config present. Prevents execution with known-bad config. |
| Unsupported parameter dropped | Toast notification + info log | JS toast: "Parameter X not supported by Y, ignored." Console log at info level. Non-fatal, generation proceeds. |
| Backend offline (model list) | Graceful degradation | Return empty model list to frontend. COMBO shows fallback. User can type model name in STRING fallback. Log info message. |
| Auth failure (401/403) | Log + graceful degradation (model list) or raise exception (generation) | Model list: return empty, log info. Generation: raise exception with auth guidance. |
| Model not loaded (text-gen-webui) | Adapter handles automatically | Check model status, load if needed (FR-19), then generate. Transparent to user. |

---

## Glossary

| Term | Definition |
|------|------------|
| **LLM_PROVIDER** | Custom ComfyUI type. Dict carrying backend URL, model name, adapter type, auth info, memory management settings (keep_alive/ttl/unload behavior). Output by Provider nodes, consumed by Generation nodes. |
| **LLM_OPTIONS** | Custom ComfyUI type. Dict of inference parameters — only params the user enabled/set (sentinel-excluded or toggle-enabled). Output by Options nodes, consumed by Advanced Generation node. |
| **LLM_META** | Custom ComfyUI type. Dict carrying provider config + options for chaining generation nodes without re-specifying config. |
| **Adapter** | Internal translation layer between generation nodes and backend HTTP APIs. Maps parameter names, applies allowlists, extracts response text. Not user-facing. |
| **Allowlist** | Per-backend list of known-accepted API parameters. Params not in the list are dropped before sending, logged at info level. |
| **Sentinel value** | A default value (typically -1 or empty string) that signals "use model default." The adapter excludes sentinel-valued params from the API request entirely. Used by Ollama Core Options. |
| **keep_alive** | Ollama parameter controlling how long a model stays loaded after a request. String format ("30s", "5m"). Timer resets per request. |
| **ttl** | LM Studio parameter controlling model idle timeout. Integer seconds. Timer resets per request. |
| **Merge-on-load** | Config strategy: `config.example.yaml` (shipped defaults) deep-merged with `config.yaml` (user overrides) at runtime. User values win. Neither file modified. |
| **Graph introspection** | Using PROMPT hidden input to reverse-index the execution graph and determine downstream connections. Used for unload deferral. |
| **defaultInput** | ComfyUI widget property. When `True`, the input renders as a connection slot instead of an inline widget, but the widget appears if nothing is connected. |

---

## Out of Scope (v0.1.0)

- Image Describe nodes (vision/image-to-text)
- Chat nodes (conversation history / multi-turn)
- Structured Output nodes (JSON schema enforcement)
- Cloud providers (OpenAI, Anthropic, Gemini, OpenRouter, Grok/xAI)
- Streaming output (complete-then-return only)
- Retry / rate limiting logic
- User-created preset management
- Preset prompt content authoring (mechanism ships, content authored separately)
- ComfyUI Registry publishing
- vLLM and standalone llama-server backends (no unload API)
- V3 node spec migration

---

## Dependencies

### Runtime
| Dependency | Version | Notes |
|------------|---------|-------|
| `pyyaml` | >=6.0 | Config file parsing |
| `requests` | >=2.28.0 | Synchronous HTTP for API calls |

### Provided by ComfyUI (not our deps)
- `pillow`, `numpy`, `aiohttp`, `torch`

### Platform
| Requirement | Version |
|-------------|---------|
| ComfyUI | V1 node spec compatible |
| Python | >=3.10 |

### External Services (user-provided)
- At least one of: LM Studio, text-generation-webui, Ollama running locally
- No backend required at install time (nodes load without errors)

---

## Assumptions

1. **AA-4:** YAML config in node pack directory is the correct pattern. Common convention, no contrary evidence.
2. **AA-6:** Dynamic model dropdowns via JS stable across ComfyUI versions. Widely used but cross-version stability unverified.
3. LM Studio and text-gen-webui silently ignore unknown top-level request params. Allowlist approach mitigates risk if they don't. Needs empirical testing.
4. text-gen-webui model list endpoint works without `--admin-key` when auth is not configured on the server.

---

## Success Criteria

1. All three Provider nodes appear in ComfyUI menu under `LLM/` category
2. Basic Generation node + any Provider node produces text output with no Options node required
3. Advanced Generation node chains two generation steps via meta passthrough; model stays loaded across chain
4. Exported workflow JSON contains zero API key values (verified by string search)
5. Model dropdown populates from running backend and refreshes on button click
6. Ollama Core Options with sentinel-valued params excludes them from request; non-sentinel values are sent
7. Config reload endpoint triggers re-read of config.yaml without ComfyUI restart
8. Node pack installs with only `pyyaml` and `requests` as new dependencies
9. User can replace existing LLM nodes in Flux prompt optimization workflow with equivalent or better results
10. text-gen-webui adapter automatically loads model before generation and unloads after last node in chain
11. Load Text File node reads user's .txt files from ComfyUI input folder

---

## Empirical Testing Items (resolve during implementation)

1. **Unknown param handling:** Ollama confirmed safe. LM Studio and text-gen-webui need testing with made-up params. Allowlist mitigates risk regardless.
2. **text-gen-webui model list without auth:** Can `GET /v1/internal/model/list` work when no auth is configured on the server?
3. **Options node height:** LM Studio (18 widgets) and text-gen-webui (24 widgets) single nodes may be too tall. Split along Ollama Core/Extra pattern if needed during implementation.

---

## Next Steps

1. User reviews and approves requirements
2. Proceed to design phase (architecture, file layout, interfaces)
3. Implementation in order: LM Studio adapter → text-gen-webui adapter → Ollama adapter
