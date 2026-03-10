# comfyui-llm-bikeshed — Resolution Tracker

Generated: 2026-02-25

## Status Key

| Status | Meaning |
|--------|---------|
| **Confirmed** | Verified against documentation or tested behavior |
| **Decided** | Deliberate choice with clear rationale |
| **Assumed** | Seemed reasonable, never actually verified |
| **Unresolved** | Known open question |
| **Contaminated** | Decision built on top of an assumption — foundation needs checking |
| **Tabled** | Deliberately deferred — not in v1 scope |
| **Moot** | No longer relevant due to other decisions |

---

## Architecture & Node Design

| # | Item | Status | Notes |
|---|------|--------|-------|
| A-1 | Options node architecture | Decided | Per-provider Options nodes. Ollama uses Core/Extra split: Core has 7 common params with sentinel values (no toggles, compact), Extra has 10 advanced params with BOOLEAN toggles (optional, chains into Core via `options_in`). LM Studio and text-gen-webui use single nodes with toggles (may split later if too tall). See design review §3. |
| A-2 | Base Options scope — which params are "universal enough" for the base node | Moot | Per-provider Options nodes chosen (A-1). Each node defines its own parameter set. Cross-provider mapping documented in `docs/reference/backend-api-parameters.md`. |
| A-3 | Per-parameter enable/disable toggles | Decided | Hybrid approach. Ollama Core uses sentinel values (no toggles). Ollama Extra, LM Studio, and text-gen-webui Options use BOOLEAN toggles (P-9 confirmed reliable). Disabled = model default, enabled = override. |
| A-4 | Options merge precedence when both Base and Ollama Options are used | Moot | Per-provider Options nodes chosen (A-1). No merge needed — one Options node type per provider. |
| A-5 | Chat node scope — predetermined chains vs interactive with session state | Tabled | Deferred from v1 scope. Concept doc lists Chat under "What This Doesn't Cover (Yet)". Needs clear decision for post-v1. |
| A-6 | Preset ↔ system prompt interaction | Decided | Separate Preset Loader node for v1. Known-working pattern (COMBO listing .txt files from `presets/` dir, output is STRING). Avoids JS widget interaction complexity. Inline COMBO→STRING approach is feasible but fragile on workflow load — future UX enhancement. |
| A-7 | Preset text storage — where shipped presets live | Decided | `presets/` directory in node pack root. Ships with README placeholder. Preset Loader node scans this directory for `.txt` files. |
| A-8 | Preset content — what the actual system prompt text is for each preset | Tabled | Presets being designed separately. Will be added when complete. Research JoyCaption's preset/description-style pattern for inspiration when authoring. |
| A-9 | Detail parameter for Image Describe — distinct from presets | Tabled | Image Describe deferred from v1 scope. |
| A-10 | Meta passthrough with provider switching — silent param dropping visibility | Decided | Allowlist filtering with info-level logging so users see dropped params in console. |
| A-11 | `IS_CHANGED = float("NaN")` on Provider node | Decided | Don't implement IS_CHANGED on Provider nodes — let ComfyUI's default caching work (output only changes when widget values change). Generation nodes use `float("NaN")` since LLM calls are non-deterministic. |
| A-12 | Structured output path per backend | Tabled | Structured Output node deferred from v1 scope. |
| A-13 | Basic vs Advanced generation node split | Decided | Two nodes: Basic (inline params + presets, compact) and Advanced (connection-only config, modular). Both share adapter layer. Whether this could be a single node remains an option but two is the safe default. |
| A-14 | Separate Provider nodes per provider vs single dropdown node | Decided | Separate nodes. Each has static widgets for its provider. All output same LLM_PROVIDER type. |
| A-15 | Model memory management — unload deferral in generation chains | Decided | Use PROMPT hidden input reverse-indexing (P-10 confirmed). Generation node checks if its meta output connects to another generation node downstream. If yes, skip unload. If no, fire unload. Ollama/LM Studio handle this naturally via TTL reset. text-gen-webui uses this mechanism for explicit unload deferral. |
| A-16 | Supported local backends | Decided | Ollama, LM Studio, text-generation-webui. Dropped vLLM and standalone llama-server (no unload API). llama.cpp supported indirectly through LM Studio and text-gen-webui. |
| A-17 | Cloud provider support | Tabled | Deferred from v1. Can be added later without breaking local-focused architecture. |
| A-19 | text-gen-webui model loading before generation | Decided | Adapter must handle full lifecycle: check model status → load if needed → generate → unload (last node only). Load/unload use admin key if configured. FR-19. |
| A-20 | Model selection priority (COMBO vs STRING fallback) | Decided | STRING `model_fallback` overrides COMBO dropdown. COMBO is convenience (auto-populated), STRING is override (offline fallback, connections). FR-21. |
| A-21 | Load Text File utility node | Decided | Separate from Preset Loader. Reads `.txt` files from ComfyUI `input/` folder (configurable). Ships with pack so users don't need external node packs for text loading. FR-20. |
| A-18 | keep_alive / ttl defaults and user configurability | Decided | User-assignable on Provider nodes. Ollama: `keep_alive`, default "30s". LM Studio: `ttl`, default 30s (note: LM Studio's app default is 60 min, but our short default prioritizes VRAM reclamation). text-gen-webui: explicit unload, see A-15. |

---

## ComfyUI Platform Behavior

| # | Item | Status | Notes |
|---|------|--------|-------|
| P-1 | `OUTPUT_IS_LIST` behavior for STRING outputs | Tabled | Only needed for Image Describe batch output (deferred from v1). Documented in ComfyUI research (`05-backend-advanced.md`). |
| P-2 | Dynamic COMBO widget behavior on workflow load with missing options | Decided | Use frontend JS + PromptServer endpoint for model lists (not backend INPUT_TYPES). Saved model name persists in `widgets_values`. JS populates COMBO from endpoint, shows fallback if backend offline. Follows comfyui-ollama pattern. |
| P-3 | COMBO → text input dynamic widget switching via JS | Decided | Not needed. Use STRING input with `defaultInput: True` as manual fallback instead. COMBO-to-text switching is complex and fragile. |
| P-4 | ComfyUI error display mechanisms | Confirmed | Exception in FUNCTION halts workflow (red outline, error notification). VALIDATE_INPUTS for pre-execution checks. Toast API for non-fatal warnings. Python logging for console output. |
| P-5 | Config reload — caching behavior | Decided | Cache on module load. Provide `/llm-bikeshed/reload-config` PromptServer endpoint. Per-execution reload is unnecessary overhead. |
| P-6 | `forceInput` behavior and serialization prevention | Confirmed | Well-documented. Prevents widget creation → no value in workflow JSON. |
| P-7 | ComfyUI widget initialization order on workflow load | Moot | Only mattered for inline COMBO→STRING preset interaction (A-6). Preset Loader node chosen instead. |
| P-8 | Batch dimension handling for IMAGE type | Confirmed | [B,H,W,C] format. Handle both [H,W,C] and [B,H,W,C] defensively. |
| P-9 | Boolean toggle widget save/load reliability | Confirmed | BOOLEAN is first-class primitive type with standard serialization. `label_on`/`label_off` parameters supported. No known save/load issues. |
| P-10 | Graph topology introspection at execution time | Confirmed | PROMPT hidden input contains full execution graph keyed by node ID. Input connections use `[source_node_id, output_index]` format. Output connections derived by reverse-indexing (iterate all nodes' inputs to find references to your node ID). Implementation pattern documented in `docs/reference/implementation-patterns.md`. |

---

## API & Provider Behavior

| # | Item | Status | Notes |
|---|------|--------|-------|
| API-1 | Anthropic model list endpoint | Tabled | Cloud providers deferred (A-17). |
| API-2 | Gemini model list endpoint | Tabled | Cloud providers deferred (A-17). |
| API-3 | Cloud provider model list endpoints — API key requirements | Tabled | Cloud providers deferred (A-17). |
| API-4 | Per-provider parameter allowlists | Confirmed | Full parameter tables documented in `docs/reference/backend-api-parameters.md`. Ollama: `additionalProperties: true`, unknown params silently ignored. LM Studio and text-gen-webui: unknown param handling needs empirical testing but allowlist approach mitigates risk. |
| API-5 | Anthropic structured output format | Tabled | Cloud providers deferred (A-17). |
| API-6 | text-gen-webui internal model management endpoints | Confirmed | load/unload/list/info endpoints confirmed. Gated behind `--admin-key` (or `--api-key` if no admin key set). |
| API-7 | text-gen-webui admin key handling | Confirmed | Supports separate `--admin-key` from `--api-key`. If admin-key not set, api-key is used for admin ops. Config should support both: `api_key` for generation, `admin_key` for model management. If only one configured, use it for both. |

---

## Infrastructure & Tooling

| # | Item | Status | Notes |
|---|------|--------|-------|
| I-1 | `requests` over `aiohttp` for HTTP | Confirmed | ComfyUI nodes execute synchronously. `asyncio.to_thread()` bridge for PromptServer endpoints. |
| I-2 | `web/` vs `js/` directory for frontend JS | Decided | Using `js/`. |
| I-3 | Error handling — raise exception, halt workflow | Decided | Exceptions for fatal errors. VALIDATE_INPUTS for pre-execution. Toast for non-fatal warnings. |
| I-4 | Rate limiting / retry logic | Decided | No retry loop in v1. Fail immediately on error. Log failure details (backend name, URL, HTTP status, response body) at error level and raise exception. Error surfaces via ComfyUI's built-in notification. Retry can be added later if transient failures prove common in practice. |
| I-5 | HTTP timeout defaults | Decided | 120s default, configurable per-provider in config.yaml. |
| I-6 | `WEB_DIRECTORY` value in `__init__.py` | Decided | `"./js"`. |
| I-7 | Config migration on node pack updates | Decided | Merge on load. `config.example.yaml` (shipped defaults) is deep-merged with user's `config.yaml` at runtime — user values always win. New keys from example appear with defaults. User-added keys preserved. Neither file is modified on disk. No migration scripts, no config versioning. |

---

## Scope & Phasing

| # | Item | Status | Notes |
|---|------|--------|-------|
| S-1 | Phase 3-4 acceptance criteria — speculative vs firm | Moot | Old phasing model (4 phases with cloud + chat + structured) superseded. v1 scope narrowed to local backends with text gen only. |
| S-2 | "v1" definition — what ships in first release | Decided | Provider nodes (3 backends) + Basic/Advanced generation nodes + per-provider Options nodes (with toggles) + adapter layer (Ollama Native + OAI-compat) + config system (config.yaml, API key resolution) + frontend JS (dynamic model dropdowns) + Preset Loader node (mechanism only, preset content authored separately). Not in v1: Image Describe, Chat, Structured Output, cloud providers, user-created presets. |
| S-3 | API key security verification test | Decided | Add explicit test: export workflow JSON, search for API key substrings, confirm zero matches. |
| S-4 | Local backend scope | Decided | Ollama, LM Studio, text-generation-webui. |
| S-5 | Cloud provider scope | Decided (tabled) | Deferred entirely from v1. |

---

## Previously Identified Assumption Audit

| # | Item | Status | Notes |
|---|------|--------|-------|
| AA-1 | System prompts work identically across local backends | Confirmed | All three local backends use `messages` array with `role: "system"`. Ollama native API uses it in `messages`. OAI-compat backends use it in `messages`. Cloud differences (Anthropic top-level, Gemini system_instruction) are tabled with cloud scope. |
| AA-2 | `requests` blocking calls work in ComfyUI node FUNCTION methods | Confirmed | Matches ecosystem pattern. |
| AA-3 | Per-provider parameter allowlists sufficient | Confirmed | Ollama ignores unknowns (`additionalProperties: true`). LM Studio/text-gen-webui need empirical testing but allowlist mitigates risk. See API-4. |
| AA-4 | YAML config in pack directory is right pattern | Assumed | Common ecosystem convention. No authoritative standard but no contrary evidence either. |
| AA-5 | IMAGE tensor format consistent across sources | Confirmed (with caveats) | [B,H,W,C] documented. Defensive code needed for squeezed tensors. |
| AA-6 | Dynamic model dropdowns stable across ComfyUI versions | Assumed | comfyui-ollama and others do it. Cross-version stability unverified but widely used pattern. |

---

## Log

| Date | Action |
|------|--------|
| 2026-02-25 | Initial tracker created from review of requirements.md and discussion |
| 2026-03-01 | Resolved A-1 (chain pattern), A-2 (base scope), A-3 (no toggles), A-4 (merge precedence). Added A-13 (Basic/Advanced split), A-14 (separate Provider nodes). Created text_gen_processing_concept.md. |
| 2026-03-07 | Reopened A-1, A-2, A-3, A-4 based on concept doc review feedback. Added A-15 (unload deferral), A-16 (backend scope), A-17 (cloud tabled), A-18 (keep_alive/ttl defaults). Added P-9, P-10. |
| 2026-03-09 | Major update from fresh research phase. Resolved: P-10 (graph introspection confirmed), P-9 (toggles confirmed), P-4 (error mechanisms confirmed), API-4 (full param tables), API-7 (admin key confirmed), A-15 (use P-10 reverse-indexing), A-1 (per-provider Options with toggles), A-3 (yes toggles), A-6 (Preset Loader node for v1), A-11 (no IS_CHANGED on Provider), AA-1 (system prompts confirmed for local backends). Marked moot: A-2, A-4, P-7, S-1. Tabled: A-5, A-9, A-12, P-1. |
| 2026-03-09 | Resolved remaining open items: S-2 (v1 scope confirmed), I-4 (no retry, fail immediately with logging), A-7 (`presets/` dir with README placeholder), A-8 (tabled, designed separately, research JoyCaption patterns later). Added I-7 (config migration — merge on load, user values always win). **All items now resolved, decided, confirmed, moot, or tabled. Zero unresolved items remain.** |
| 2026-03-10 | Design review update. Added A-19 (text-gen-webui model load before generation), A-20 (model selection priority — STRING fallback overrides COMBO), A-21 (Load Text File utility node). Updated A-1 (Ollama Core/Extra split — sentinel values for common, toggles for advanced) and A-3 (hybrid: sentinels for Ollama Core, toggles everywhere else). Updated requirements.md with FR-19, FR-20, FR-21, US-14, new ACs for model fallback priority and auth-first model list endpoints. max_tokens default raised to 1024. |
