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
| **Proposed** | Documented stakeholder direction — not implemented or not yet promoted to Decided |
| **Moot** | No longer relevant due to other decisions |

---

## Architecture & Node Design

| # | Item | Status | Notes |
|---|------|--------|-------|
| A-1 | Options node architecture | Decided | Per-provider Options nodes for LM Studio, Textgen, and OpenAI (toggle pattern). **Superseded detail (D-3, 2026-05-12):** in-pack Ollama Core/Extra split removed with Ollama surface; see `docs/proposals/ollama-removal-plan.md`. |
| A-2 | Base Options scope — which params are "universal enough" for the base node | Moot | Per-provider Options nodes chosen (A-1). Each node defines its own parameter set. Cross-provider mapping documented in `docs/reference/backend-api-parameters.md`. |
| A-3 | Per-parameter enable/disable toggles | Decided | BOOLEAN toggles on LM Studio, text-gen-webui, and OpenAI Options (P-9 confirmed reliable). **Moot (D-3):** hybrid “Ollama Core sentinels” language referred to removed nodes. |
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
| A-15 | Model memory management — unload deferral in generation chains | Decided | Use PROMPT hidden input reverse-indexing (P-10 confirmed). Generation node checks if its meta output connects to another generation node downstream. If yes, skip unload. If no, fire unload. LM Studio TTL behavior and text-gen-webui explicit unload deferral per this mechanism. **[VERIFY] empirical:** mid-chain TTL extension (`max(ttl*10, 300)`) and Textgen defer-unload on live backends. |
| A-16 | Supported local backends | Decided | **In-pack:** LM Studio, text-generation-webui (OpenAI API via same OAI-compat adapter). **Removed (D-3):** native Ollama. Dropped vLLM and standalone llama-server (no unload API). llama.cpp supported indirectly through LM Studio and text-gen-webui. |
| A-17 | Cloud provider support | Tabled | Deferred from v1. Can be added later without breaking local-focused architecture. |
| A-19 | text-gen-webui model loading before generation | Decided | Adapter must handle full lifecycle: check model status → load if needed → generate → unload (last node only). Load/unload use admin key if configured; `model/info` and chat use API key when set — see `textgen-lifecycle-verified.md`. FR-19. **[VERIFY] empirical:** full load→generate→unload chain on live Textgen with distinct api/admin keys. |
| A-20 | Model selection priority (COMBO vs STRING fallback) | Decided | STRING `model_fallback` overrides COMBO dropdown. COMBO is convenience (auto-populated), STRING is override (offline fallback, connections). FR-21. |
| A-21 | Load Text File utility node | Decided | Separate from Preset Loader. Reads `.txt` files from ComfyUI `input/` folder (configurable). Ships with pack so users don't need external node packs for text loading. FR-20. |
| A-18 | keep_alive / ttl defaults and user configurability | Decided | User-assignable on lifecycle (LM Studio TTL/context) and provider-adjacent settings where applicable. LM Studio: `ttl`, default 30 s on lifecycle node (pack VRAM tuning; LM Studio app default idle TTL is 60 min when omitted — see `lm-studio-lifecycle-verified.md`). text-gen-webui: explicit unload, see A-15. **Moot (D-3):** Ollama `keep_alive` on a dedicated provider node. **[VERIFY] empirical:** TTL reset per request in chain on live LM Studio. |
| A-22 | LM Studio explicit model load with context_length | Decided | `LLM Lifecycle: LM Studio` node supplies `context_length` (0 = model default). Adapter calls `GET /api/v1/models` (`models[].key`, `loaded_instances[].config.context_length`), `POST /api/v1/models/load` with `context_length` if needed, `POST /api/v1/models/unload` with `loaded_instances[].id` as `instance_id` when last in chain. Mirrors text-gen-webui lifecycle pattern. JIT bug (#1463) cited for explicit load — **[VERIFY]** issue status + empirical load/unload on live LM Studio. Tier 1 audit (2026-06-07): REST response parse fixed in `oai_compat.py`; see `lm-studio-lifecycle-verified.md`. |
| A-23 | OpenAI API — Chat Completions core slice | Decided | Separate Provider (`backend: openai`) and Options nodes. Non-streaming `POST /v1/chat/completions` with core sampling allowlist (`temperature`, `top_p`, `max_tokens`, `max_completion_tokens`, `stop`, `seed`, penalties). If both token limits are set, `max_completion_tokens` wins. No local model load/unload or LM-only `ttl`. Model list via `GET /v1/models` (same shape as OAI). API keys only from `config.yaml` / env (`LLM_BIKESHED_OPENAI_API_KEY`), never workflow JSON. Tools, streaming, JSON mode, multimodal — deferred (see README out-of-scope). |
| A-24 | Textgen lifecycle node requires a visible widget | Confirmed | ComfyUI often renders nodes with `INPUT_TYPES["required"] == {}` as title + output only. `LLM Lifecycle: Textgen` uses BOOLEAN `manage_model_memory` (default ON); OFF yields empty `{}` lifecycle dict (no VRAM management). |

---

## ComfyUI Platform Behavior

| # | Item | Status | Notes |
|---|------|--------|-------|
| P-1 | `OUTPUT_IS_LIST` behavior for STRING outputs | Tabled | Only needed for Image Describe batch output (deferred from v1). Documented in external ComfyUI reference corpus (`05-backend-advanced.md`; see `docs/research/external-comfyui-reference-corpus.md`). |
| P-2 | Dynamic COMBO widget behavior on workflow load with missing options | Decided | Use frontend JS + PromptServer endpoint for model lists (not backend INPUT_TYPES). Saved model name persists in `widgets_values`. JS populates COMBO from endpoint, shows fallback if backend offline. Ecosystem pattern for dynamic refresh COMBOs. |
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
| API-4 | Per-provider parameter allowlists | Confirmed | Full parameter tables documented in `docs/reference/backend-api-parameters.md`. LM Studio and text-gen-webui: unknown param handling needs empirical testing but allowlist approach mitigates risk. **Moot (D-3):** Ollama-specific `additionalProperties` note referred to removed adapter. |
| API-5 | Anthropic structured output format | Tabled | Cloud providers deferred (A-17). |
| API-6 | text-gen-webui internal model management endpoints | Confirmed | load/unload/list use `--admin-key` when set; `GET /v1/internal/model/info` uses `--api-key` (`check_key`), not admin — see `textgen-lifecycle-verified.md`. Upstream-verified 2026-05-12 / re-checked 2026-06-07. |
| API-7 | text-gen-webui admin key handling | Confirmed | Supports separate `--admin-key` from `--api-key`. If admin-key not set, api-key is used for admin ops. Config should support both: `api_key` for generation, `admin_key` for model management. If only one configured, use it for both. |
| API-8 | OpenAI Chat Completions — provider slice | Confirmed | Same HTTP surface as LM Studio OAI path for chat (`/v1/chat/completions`) and models (`/v1/models`). Backend id `openai` skips Textgen/LM-only lifecycle APIs. Parameter surface intentionally smaller than full OpenAI API (see A-23). |
| API-9 | Textgen model list source | Confirmed | For backend `text_gen_webui`, prefer `GET /v1/internal/model/list` (authoritative vs UI) before `GET /v1/models`. Implemented in `model_list._sync_resolve_oai_compat_models` with `get_textgen_auth_keys()` for credentials. |

---

## Documentation & reference corpus

| # | Item | Status | Notes |
|---|------|--------|-------|
| DOC-1 | Off-repo ComfyUI custom-node reference corpus (`D:\ai\tmp\comfyui-custom-nodes-research\`) | Unresolved | Feb 2026 scratch mirror of official docs; not in git; partially superseded by `docs/reference/` and `docs/the-archive/`. Inventory and disposition options in `docs/research/external-comfyui-reference-corpus.md`. Hardcoded path removed from `CLAUDE.md` and `implementation-patterns.md` (2026-06-08). Pending owner decision: vendor, drop, or hybrid. |
| DOC-2 | `comfyui-node-standards.md` ("project memory") | Unresolved | Referenced in old agent guidance; file never committed to repo or external corpus. Do not cite until located or rewritten. |

---

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
| S-2 | "v1" definition — what ships in first release | Decided | **As of D-3 execution:** OAI Compatible provider + OpenAI path within same node; lifecycle nodes; Basic/Advanced generation; per-provider Options (LM Studio, Textgen, OpenAI); **single** OAI-compat adapter + config + JS dropdowns + Preset Loader. **Removed:** in-pack Ollama native surface. Not in v1: Image Describe, Chat, Structured Output, extra cloud providers, user-created presets. |
| S-3 | API key security verification test | Decided | Add explicit test: export workflow JSON, search for API key substrings, confirm zero matches. |
| S-4 | Local backend scope | Decided | LM Studio, text-generation-webui. Native Ollama removed from pack (D-3). |
| S-5 | Cloud provider scope | Decided (tabled) | Deferred entirely from v1. |

---

## Previously Identified Assumption Audit

| # | Item | Status | Notes |
|---|------|--------|-------|
| AA-1 | System prompts work identically across local backends | Confirmed | LM Studio / text-gen-webui / OpenAI Chat use `messages` array with `role: "system"`. Cloud differences (Anthropic top-level, Gemini system_instruction) are tabled with cloud scope. **Moot (D-3):** in-pack Ollama native path. |
| AA-2 | `requests` blocking calls work in ComfyUI node FUNCTION methods | Confirmed | Matches ecosystem pattern. |
| AA-3 | Per-provider parameter allowlists sufficient | Confirmed | LM Studio/text-gen-webui need empirical testing but allowlist mitigates risk. See API-4. **Moot (D-3):** Ollama “ignores unknowns” note. |
| AA-4 | YAML config in pack directory is right pattern | Assumed | Common ecosystem convention. No authoritative standard but no contrary evidence either. |
| AA-5 | IMAGE tensor format consistent across sources | Confirmed (with caveats) | [B,H,W,C] documented. Defensive code needed for squeezed tensors. |
| AA-6 | Dynamic model dropdowns stable across ComfyUI versions | Assumed | comfyui-ollama and others do it. Cross-version stability unverified but widely used pattern. |

---

## Proposed direction (not yet implemented)

Intent is spelled out in [`docs/proposals/product-direction-and-scope.md`](proposals/product-direction-and-scope.md). Rows here make roadmap shifts visible next to older Confirmed/Decided entries; they are **not** authoritative for implementation until reviewed and promoted.

| # | Item | Status | Notes |
|---|------|--------|-------|
| D-1 | Textgen-first delivery priority | Proposed | Align engineering attention with Textgen + shared core before broadening surface area. |
| D-2 | Lifecycle UX and architecture rethink | Proposed | Existing lifecycle code and `textgen-rehaul` lifecycle manager design are not treated as validated user UX; expect a full rethink before major investment. |
| D-3 | Remove Ollama from this pack | Decided | **Shipped 2026-05-12** — native adapter, provider/options nodes, `/llm-bikeshed/models/ollama`, shipped `providers.ollama` example removed; see [`ollama-removal-plan.md`](proposals/ollama-removal-plan.md) and `CHANGELOG.md` [0.3.0]. URL detection may still return backend id `ollama` for OAI-compat labeling only. |
| D-4 | Dedicated llama.cpp integration | Tabled | After Textgen and core generation are solid; indirect use via LM Studio / Textgen unchanged. |

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
| 2026-05-12 | Added **Proposed** status key entry and Proposed direction table (D-1–D-4) pointing to `docs/proposals/product-direction-and-scope.md` (Textgen-first, lifecycle rethink, Ollama removal intent, llama.cpp deferral). |
| 2026-05-12 | **D-3 executed:** removed in-pack Ollama (adapter, nodes, `/models/ollama`, config example); semver **0.3.0**; tracker rows reconciled. See `docs/proposals/ollama-removal-plan.md`. |
| 2026-05-12 | Linked D-3 execution checklist: `docs/proposals/ollama-removal-plan.md`. |
| 2026-06-07 | Tier 1 provenance audit: LM Studio lifecycle REST parse + instance_id unload fixed; `[VERIFY]` flags on A-15, A-18, A-19, A-22; API-6 note corrected; research notes `lm-studio-lifecycle-verified.md`, `audit-handoff.md` checklist complete. |
| 2026-06-08 | Documented off-repo ComfyUI reference corpus (DOC-1, DOC-2); added `docs/research/external-comfyui-reference-corpus.md`; removed hardcoded `D:\ai\tmp\` pointers from `CLAUDE.md` and `implementation-patterns.md`. |
| 2026-06-08 | Tier 1 audit session (fresh-context prompt): code re-read confirmed no drift since 2026-06-07; empirical QA protocol added to `audit-handoff.md`; `[VERIFY]` on A-15, A-18, A-19, A-22 unchanged (no empirical runs). |
| 2026-06-08 | **Audit reframe:** Tier 1 redefined as project-wide provenance sweep (tracker contamination, research claim inventory, reference/concept vs code, citation freshness). Empirical Textgen/LM Studio cancel QA demoted to optional subsidiary track. `audit-handoff.md`, `fresh-context-audit-prompt.md`, `provenance-and-reverification.md` §5 updated. Systematic Tier 1.1 tracker audit **pending**. |
