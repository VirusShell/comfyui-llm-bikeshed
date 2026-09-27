# Pack systems map (pre-overhaul)

**Date:** 2026-09-27  
**Status:** Docs-only orientation for Vir. Describes how surfaces compose **today**. Hypotheses are labeled; this is **not** a ship plan.  
**Scope:** Connection, legacy providers, lifecycle, generate, options, utils, socket types — composition, overlap, debt.  
**Non-goals:** No V3 spike, no registry work, no implementing Options split/polish, no product overhaul in this note.

Sources (cite, don’t re-invent): [`CODEBASE.md`](../../CODEBASE.md), [`README.md`](../../README.md), [`docs/text_gen_processing_concept.md`](../text_gen_processing_concept.md), [`docs/resolution_tracker.md`](../resolution_tracker.md) (A-25, D-2, A-15/A-18/A-22), [`docs/qol-backlog.md`](../qol-backlog.md), [`docs/proposals/product-direction-and-scope.md`](../proposals/product-direction-and-scope.md), [`docs/research/cancel-interrupt-status.md`](cancel-interrupt-status.md), [`docs/research/textgen-lifecycle-verified.md`](textgen-lifecycle-verified.md), [`docs/research/lm-studio-lifecycle-verified.md`](lm-studio-lifecycle-verified.md), [`docs/research/user-feedback-2026-06-17.md`](user-feedback-2026-06-17.md), Connection docs lead `2be26be`, worklist `7ad0758`.

---

## 1. Job of each surface

Plain-language “what is this node *for*” — not a full widget catalog.

### LLM Connection (`LLMConnection`) — **recommended entry**

One adaptive node: host mode (Auto or pin LM Studio / Textgen / llama.cpp / OpenAI / Generic), URL + model, on-node VRAM face knobs for Textgen (`manage_model_memory`) and LM Studio (`ttl` / `context_length`), optional `ensure_load_on_select` (UI-only; JS → `POST /llm-bikeshed/models/ensure-loaded`). Outputs **`LLM_PROVIDER`**. No API-key widgets. Status chrome + Refresh Models via `POST /llm-bikeshed/models/connection`. Prefer this over Provider + Lifecycle for new graphs (`README`, `CODEBASE`, `2be26be`).

### Legacy: LLM Provider OAI Compatible (`LLMProviderOAICompat`)

Fingerprints backend at URL; optional **`LLM_LIFECYCLE`** input. Models via `/llm-bikeshed/models/oai-compat`. Still first-class for mixed/migrated graphs and llama.cpp `/v1` when not using Connection. Hint-logs when detected backend is Textgen (“prefer Textgen provider”). Sets `load_before_generate` True when backend is Textgen even without lifecycle (unload still lifecycle-gated).

### Legacy: LLM Provider Textgen (`LLMProviderTextGenWebUI`)

Textgen-only URL/defaults; no fingerprinting; models via `/llm-bikeshed/models/textgen`. On-node `manage_model_memory` embeds the same lifecycle dict the separate Textgen lifecycle node would produce. Redundant with Lifecycle: Textgen for new Textgen graphs (A-25 / feedback).

### Lifecycle: LM Studio / Textgen (`LLMLifecycle*`)

Output **`LLM_LIFECYCLE`** only. Wire into **OAI Compatible’s** `lifecycle` input (not into Connection — Connection embeds the face). LM Studio: `ttl` + `context_length`. Textgen: `manage_model_memory` BOOLEAN (needed so ComfyUI renders the node — A-24). Product direction: lifecycle **UX** still under full rethink (D-2); code is operational, not “final mental model.”

### Generate Basic (`LLMGenerate`)

Compact: `provider` + prompt/system + inline temperature / max_tokens / seed. Returns `(text, LLM_META)`. Always re-runs (`IS_CHANGED` → NaN). Sets `skip_unload` via graph introspection when another gen node is downstream on `meta` (A-15 / P-10).

### Generate Advanced (`LLMGenerateAdvanced`)

Modular: `provider`, optional **`LLM_OPTIONS`**, optional upstream **`LLM_META`**. Explicit provider/options override meta. Same meta out + `skip_unload` behavior. Seed always applied on Advanced.

### Options: LM Studio / OpenAI / Textgen (`LLMOptions*`)

Per-backend sampling params with enable toggles; only ON params enter the dict (`options_base.build_toggle_options`). Wire into Advanced’s `options`. Optional — disconnect → model defaults. Tall walls: Textgen ~12 params × enable = ~24 widgets; LM Studio ~9 × enable = ~18 (`qol-backlog`). Helper supports `options_in` merge, but **shipped Options nodes do not expose an `options_in` socket** in `INPUT_TYPES` today.

### Utilities: Preset Loader / Load Text File

STRING sources for `system_prompt` / `prompt`. Presets from pack `presets/`; Load Text from ComfyUI input folder. Separate from provider/options story (A-6).

### Socket types (plain dicts, string type names)

| Socket | Typical contents | Flows |
|--------|------------------|--------|
| **`LLM_PROVIDER`** | `backend`, `adapter` (`oai_compat`), `url`, `model`, `timeout`, optional `lifecycle`, `load_before_generate` | Connection / Providers → Generate |
| **`LLM_LIFECYCLE`** | `{type: lm_studio\|text_gen_webui, …}` | Lifecycle → OAI Compatible only (legacy) |
| **`LLM_OPTIONS`** | Toggle-selected sampling keys | Options → Advanced |
| **`LLM_META`** | `{provider: public_provider(...), options}` — **no secrets** | Gen → Gen chaining; Advanced can ingest |

Secrets never live in these dicts; adapters resolve keys at HTTP time (`config.auth`).

---

## 2. How they compose

### Typical graphs (today)

```text
A) Recommended minimal
   LLM Connection  --LLM_PROVIDER-->  Generate Basic  --> text
                                              \--> LLM_META (unused)

B) Recommended advanced
   Connection --> Advanced
   Options*   --LLM_OPTIONS--> Advanced
   (optional Preset/Load Text --> prompt / system_prompt)

C) Legacy OAI + lifecycle
   Lifecycle LM|Textgen --LLM_LIFECYCLE--> OAI Compatible --LLM_PROVIDER--> Gen

D) Legacy Textgen provider
   Textgen Provider (manage_model_memory ON) --> Gen
   (no separate Lifecycle needed)

E) Meta chaining
   Gen1 --meta--> Gen2 --meta--> Gen3
   Mid nodes: skip_unload=True; last node: unload / TTL settle if lifecycle active
```

Shipped examples: `example_workflows/connection_basic.json` (A); `basic_generation.json` / `textgen_basic.json` / `advanced_with_options.json` (legacy C/D/B-shaped).

### What’s redundant now that Connection exists

| Legacy path | Connection equivalent |
|-------------|------------------------|
| OAI Compatible + Lifecycle LM Studio | Connection host LM Studio / Auto + `ttl` / `context_length` face |
| OAI Compatible + Lifecycle Textgen | Connection Textgen face + `manage_model_memory` |
| Textgen Provider + embedded memory toggle | Connection Textgen face |
| Separate `/models/oai-compat` + `/detect` UX | `/models/connection` + host_mode |

Legacy nodes stay registered so old workflows keep working (`README` Legacy section). New graphs should not need Provider+Lifecycle pairs.

### Shared under the hood

All providers still produce the same **`LLM_PROVIDER`** shape and call the single **`oai_compat`** adapter (`adapters/oai_compat.py`). Generation, allowlists, Textgen load/unload, LM Studio TTL/load/unload, and cancel polling are one path. Dual *nodes* ≠ dual *adapters*.

---

## 3. Conflicts / debt (cite in-repo; don’t invent)

### Dual provider story (A-25, feedback 2026-06-17)

Three ways to say “talk to Textgen”: Connection Textgen face, Textgen Provider, or OAI Compatible URL pointed at Textgen (+ optional Lifecycle). Lifecycle sockets only attach to OAI Compatible; Textgen Provider already embeds the same toggle. Tracker: A-25 Unresolved → D-2 rethink. Connection docs lead demoted legacy in README/CODEBASE but did not remove nodes.

### Options walls

Tall toggle nodes (qol-backlog: evaluate Textgen / LM Studio height). Worklist **defers** Options height polish until systems direction says Options stay. Split vs keep vs fold into Advanced/Connection is open (see §4). `options_in` merge exists in helper but is unused by node INPUT_TYPES — latent API, not a user-facing chain today.

### Auth / status uneven

- Keys: config/env only; OAI-shaped fallback via `providers.oai_compat`; Textgen dual api/admin keys (`get_textgen_auth_keys`) — documented in README / `textgen-lifecycle-verified.md`.
- Status chrome: Connection has richer face (detected/effective/loaded/auth hint). Legacy providers use `model_dropdown.js` status widgets (P-12 fixed). Headless/API mode: `/llm-bikeshed/*` client routes **not** API-mode compatible; generation still works from baked URL/model in graph JSON (`CODEBASE`).
- No browser set-key / reload-config in normal user path (tracker once mentioned reload endpoint; product still “edit yaml + restart ComfyUI” in README).

### `ensure_load_on_select` policy

Connection widget default **OFF**; URL changes never load; model-dropdown change may POST ensure-loaded when ON (`CODEBASE` / `llm_connection.js`). Python `build_provider` marks the flag UI-only (`ARG002`) — does **not** enter `LLM_PROVIDER`. Load-at-queue still driven by `load_before_generate` + lifecycle inside the adapter. Policy surface is frontend + ensure-loaded route, not the provider dict.

### Cancel / VRAM gaps (documented)

From [`cancel-interrupt-status.md`](cancel-interrupt-status.md):

- ComfyUI Cancel **unblocks** the execution thread (interruptible HTTP) for generation/lifecycle GETs used that way.
- **Textgen:** host stop via `POST /v1/internal/stop-generation` — empirical PASS (v4.9, 2026-06-17).
- **LM Studio:** no stop API in pack — empirical FAIL/expected (v0.4.16); inference can continue after Cancel.
- **No unload-on-interrupt:** successful-path unload only; interrupt can leave model loaded (product choice unresolved).
- Lifecycle chain empirical QA (A-15 / A-18 / A-19 / A-22) still open; worklist defers behind systems direction.

VRAM sharing intent remains core (`CODEBASE` purpose; concept doc A-15/A-18): Textgen explicit load/unload; LM Studio TTL (+ explicit load for context — JIT #1463 still open per lm-studio research note).

---

## 4. Keep / demote / kill — *hypotheses* (not recommendations to ship)

Label: **hypothesis**. Ask Vir before any overhaul.

| Surface | Hypothesis | Notes |
|---------|------------|--------|
| **LLM Connection** | **Keep** as primary connectivity | Already documented lead (`2be26be`). |
| **OAI Compatible provider** | **Demote** in docs/UX; possibly long-lived compatibility | Still useful for exotic OAI hosts / old graphs; overlapping with Connection Auto. |
| **Textgen provider** | **Demote** or eventually fold into Connection | A-25 overlap; Connection Textgen face covers new work. |
| **Lifecycle nodes** | **Demote** for new graphs; fate tied to D-2 | Only needed for legacy OAI Compatible wiring. |
| **Generate Basic + Advanced** | **Keep** split for now (A-13 decided) | *Hypothesis:* someday one node with optional breakouts — not proposed here. |
| **Options nodes** | **Open — might go away, merge, or stay** | Height debt + backend-specific walls. Alternatives (*hypotheses*): fold common knobs into Advanced; single Options with backend allowlist; keep toggles but split/collapse UI. **Do not implement Options polish until this is answered** (worklist). |
| **Preset / Load Text** | **Keep** | Independent STRING utilities. |
| **Socket types** | **Keep** `PROVIDER` / `OPTIONS` / `META`; **`LIFECYCLE` may shrink** if Connection-only world wins | *Hypothesis:* lifecycle becomes fields-only inside PROVIDER (already true on Connection). |

---

## 5. Open questions for Vir (product choices — not height polish)

1. **Canonical connectivity:** Is Connection the only *taught* path, with legacy providers frozen indefinitely, or is there a timeline to unregister / hide them?
2. **Lifecycle mental model (D-2):** Stay “face knobs on Connection,” revive separate Lifecycle nodes, or a different VRAM metaphor entirely?
3. **Options future:** Keep per-backend Options nodes, merge into Advanced/Connection, or replace with a thinner sampling surface? (Height polish blocked on this.)
4. **Basic vs Advanced:** Keep two generate nodes, or converge once Options direction is clear?
5. **Interrupt + VRAM policy:** On Cancel, should Textgen/LM Studio **unload**, leave loaded, or defer — and is LM Studio “Cancel doesn’t stop GPU” acceptable as documented limit?
6. **`ensure_load_on_select`:** Stay default OFF forever, or become part of a clearer “when does the pack load weights?” story with Manage model memory?
7. **Auth UX:** Stay yaml/env + restart only, or invest in status/reload so Connection’s auth hint is actionable without doc diving?
8. **llama.cpp:** Connection/OAI `/v1` forever enough, or revisit dedicated node later (D-4 still tabled)?

---

## 6. Non-goals of this note

- No ComfyUI **V3** node API spike  
- No Comfy Registry / publish changes  
- No implementing Options split, height collapse, or provider deletion  
- No resolving D-2 / A-25 in code — only framing for Vir  

---

## Quick diagram (mental model)

```text
                    ┌─ (legacy) Lifecycle ─┐
                    │                      ▼
 Connection ────┐   │              OAI Compatible ──┐
 Textgen Prov. ─┼───┴───────────────────────────────┤
                │         LLM_PROVIDER              ▼
                └─────────────────────────────► Generate Basic
 Options* ──LLM_OPTIONS───────────────────────► Generate Advanced
                                                    │
                                              LLM_META chain
                                                    ▼
                                              Generate …
```

Adapter underneath: always `oai_compat` → `POST {url}/v1/chat/completions` (+ Textgen `/v1/internal/model/*`, LM Studio TTL / `/api/v1/models/*` when lifecycle present).

---

## Related worklist

Live queue: [`WORKLIST.md`](../../WORKLIST.md) — systems map item should point here; Options height remains deferred until Vir answers §5 item 3.
