# Pack systems map (pre-overhaul)

**Date:** 2026-09-27  
**Status:** **NOT greenlit.** Docs-only orientation for Vir. Describes how surfaces compose **today**. Hypotheses are labeled; this is **not** a ship plan and **not** an implementation list. Options height polish stays deferred. Vir Q1 is answered: legacy providers remain only for compatibility/testing and existing workflows until the Connection path is confirmed; then unregister/hide them. This does **not** greenlight unrelated overhaul code.
**Vir Q2 (Lifecycle / VRAM) is answered (2026-09-28):** For new graphs, Connection owns VRAM through one user-facing **Manage VRAM / Manage memory** toggle. The backend may be detected or pinned; the pack sends the backend-appropriate load/unload/TTL commands. Textgen and LM Studio keep their existing API paths under that single-toggle metaphor. llama.cpp VRAM management is setup-gated: only when the host exposes router `/models/load` and `/models/unload`; otherwise chat still works and the toggle is hidden/inert with status. This docs lock does **not** greenlight implementing the unified toggle or any unrelated overhaul code.
**Scope:** Connection, legacy providers, lifecycle, generate, options, utils, socket types - composition, overlap, debt.  
**Non-goals:** No V3 spike, no registry work, no implementing Options split/polish, no product overhaul in this note.

**Pack tip (this fold):** `0250577` base + 2026-09-28 `model` vs `loaded_model` sync smell fold. Prior fold tip was `0250577` (comfydesk systems deltas). Comfydesk note was written against pack tip `7ad0758`.

**External provenance:** comfydesk systems map — `D:\ai\bot-grok\comfydesk\notes\2026-09-27-bikeshed-systems-map.md` (cite below as **“comfydesk 2026-09-27 systems map”**). Pack structure kept; their deltas folded in.

Sources (cite, don't re-invent): [`CODEBASE.md`](../../CODEBASE.md), [`README.md`](../../README.md), [`docs/text_gen_processing_concept.md`](../text_gen_processing_concept.md), [`docs/resolution_tracker.md`](../resolution_tracker.md) (A-1, A-13, A-25, D-2, A-15/A-18/A-22), [`docs/qol-backlog.md`](../qol-backlog.md), [`docs/proposals/product-direction-and-scope.md`](../proposals/product-direction-and-scope.md), [`docs/research/cancel-interrupt-status.md`](cancel-interrupt-status.md), [`docs/research/textgen-lifecycle-verified.md`](textgen-lifecycle-verified.md), [`docs/research/lm-studio-lifecycle-verified.md`](lm-studio-lifecycle-verified.md), [`docs/research/user-feedback-2026-06-17.md`](user-feedback-2026-06-17.md), Connection docs lead `2be26be`, worklist `7ad0758` / `6a0dc86`, **comfydesk 2026-09-27 systems map**, **2026-09-28 dig** (`model` vs `loaded_model` selector/status).

---

## TLDR (intended spine)

*(Provenance: comfydesk 2026-09-27 systems map; aligned with pack sections below.)*

Twelve registered nodes form **five product layers** that share **four** dict sockets (`LLM_PROVIDER`, `LLM_LIFECYCLE`, `LLM_OPTIONS`, `LLM_META`):

| Layer | Surfaces |
|-------|----------|
| Connection | `LLM Connection` |
| Legacy providers + Lifecycle | OAI Compatible, Textgen provider, Lifecycle LM/Textgen |
| Options | LM Studio / OpenAI / Textgen Options |
| Generate | Basic, Advanced |
| Utils | Preset Loader, Load Text File |

**Intended new-graph spine:** **Connection → Generate Basic**. Connection owns new-graph VRAM management through one backend-adaptive **Manage VRAM / Manage memory** toggle; there are no extra lifecycle knobs that do not apply. Textgen and LM Studio retain their existing API paths behind that metaphor. llama.cpp only gets VRAM management when its host exposes router `/models/load` and `/models/unload`; otherwise chat remains available and the toggle is hidden/inert with status. Modular work adds **Options → Advanced** (Options are **orthogonal to Connection** - they attach only to Advanced; Basic inlines temp/max_tokens/seed). Optional **meta chaining** across gen nodes. Legacy Provider + Lifecycle still emit the same `LLM_PROVIDER` shape and remain temporarily registered for compatibility/testing and existing workflows while the Connection path is confirmed; then unregister/hide them rather than maintain a second product.

The old VRAM split is resolved directionally for new graphs: one Connection toggle, with backend-specific API behavior behind it; the separate Lifecycle path remains legacy/compatibility only. The remaining product call is **three ways to build a provider**. Options stay/go is a separate spine question (separate nodes vs widgets-on-gen), not height polish.

---

## 1. Job of each surface

Plain-language "what is this node *for*" - not a full widget catalog.

### LLM Connection (`LLMConnection`) - **recommended entry**

One adaptive node: host mode (Auto or pin LM Studio / Textgen / llama.cpp / OpenAI / Generic), URL + model, and one user-facing **Manage VRAM / Manage memory** toggle for new graphs. The backend may be detected or pinned; the pack sends the appropriate load/unload/TTL commands. Textgen and LM Studio keep their existing API paths behind the toggle. llama.cpp VRAM management is setup-gated: only use/show it when the host exposes router `/models/load` and `/models/unload`; otherwise chat still works and the toggle is hidden/inert with status. No extra backend-specific lifecycle knobs are added to this surface. Optional `ensure_load_on_select` remains UI-only (`POST /llm-bikeshed/models/ensure-loaded`). Outputs **`LLM_PROVIDER`**. No API-key widgets. Status chrome + Refresh Models via `POST /llm-bikeshed/models/connection`. Prefer this over Provider + Lifecycle for new graphs (`README`, `CODEBASE`, `2be26be`).

### Legacy: LLM Provider OAI Compatible (`LLMProviderOAICompat`)

Fingerprints backend at URL; optional **`LLM_LIFECYCLE`** input. Models via `/llm-bikeshed/models/oai-compat`. Still first-class for mixed/migrated graphs and llama.cpp `/v1` when not using Connection. Hint-logs when detected backend is Textgen ("prefer Textgen provider"). Sets `load_before_generate` True when backend is Textgen even without lifecycle (unload still lifecycle-gated).

**Code-voice lag** *(comfydesk 2026-09-27 systems map):* OAI Compatible docstring/log still steers Textgen fingerprints toward the **Textgen provider**, while README / Connection lead prefer **Connection** for new graphs. Dual product voice until docs/code strings align.

### Legacy: LLM Provider Textgen (`LLMProviderTextGenWebUI`)

Textgen-only URL/defaults; no fingerprinting; models via `/llm-bikeshed/models/textgen`. On-node `manage_model_memory` embeds the same lifecycle dict the separate Textgen lifecycle node would produce. Redundant with Lifecycle: Textgen for new Textgen graphs (A-25 / feedback).

### Lifecycle: LM Studio / Textgen (`LLMLifecycle*`)

Output **`LLM_LIFECYCLE`** only. These nodes remain the legacy/compatibility path: wire into **OAI Compatible's** `lifecycle` input, not into Connection. They are not being revived for new graphs; Connection owns the single VRAM toggle there. Existing LM Studio (`ttl` / `context_length`) and Textgen (`manage_model_memory`) API behavior remains available behind the Connection metaphor. The implementation follow-up is still ask-first; this docs decision is not a code green light.

### Generate Basic (`LLMGenerate`)

Compact: `provider` + prompt/system + inline temperature / max_tokens / seed. Returns `(text, LLM_META)`. Always re-runs (`IS_CHANGED` → NaN). Sets `skip_unload` via graph introspection when another gen node is downstream on `meta` (A-15 / P-10).

### Generate Advanced (`LLMGenerateAdvanced`)

Modular: `provider`, optional **`LLM_OPTIONS`**, optional upstream **`LLM_META`**. Explicit provider/options override meta. Same meta out + `skip_unload` behavior. Seed always applied on Advanced.

### Options: LM Studio / OpenAI / Textgen (`LLMOptions*`)

Per-backend sampling params with enable toggles; only ON params enter the dict (`options_base.build_toggle_options`). Wire into Advanced's `options`. Optional - disconnect → model defaults. Tall walls: Textgen ~12 params x enable = ~24 widgets; LM Studio ~9 x enable = ~18 (`qol-backlog`). Helper supports `options_in` merge, but **shipped Options nodes do not expose an `options_in` socket** in `INPUT_TYPES` today.

### Utilities: Preset Loader / Load Text File

STRING sources for `system_prompt` / `prompt`. Presets from pack `presets/`; Load Text from ComfyUI input folder. Separate from provider/options story (A-6).

### Socket types (plain dicts, string type names)

| Socket | Typical contents | Flows |
|--------|------------------|--------|
| **`LLM_PROVIDER`** | `backend`, `adapter` (`oai_compat`), `url`, `model`, `timeout`, optional `lifecycle`, `load_before_generate` | Connection / Providers → Generate |
| **`LLM_LIFECYCLE`** | `{type: lm_studio\|text_gen_webui, …}` | Lifecycle → OAI Compatible only (legacy) |
| **`LLM_OPTIONS`** | Toggle-selected sampling keys | Options → Advanced |
| **`LLM_META`** | `{provider: public_provider(...), options}` - **no secrets** | Gen → Gen chaining; Advanced can ingest |

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

### Examples inventory (what ships vs what's missing)

*(Provenance: comfydesk 2026-09-27 systems map.)*

| File | Nodes | Family path |
|------|-------|-------------|
| `example_workflows/connection_basic.json` | Connection + Generate Basic | **A** (docs lead) |
| `basic_generation.json` | OAI Compatible + Generate Basic | **C**-shaped without Lifecycle |
| `textgen_basic.json` | Textgen provider + Generate Basic | **D** |
| `advanced_with_options.json` | OAI Compatible + Options LM Studio + Generate Advanced | **B**-shaped with **legacy** provider |

**Not in examples today:** Lifecycle nodes; **Connection + Options + Advanced** (recommended B); meta-chain graphs; OpenAI Options; Textgen Options.

CODEBASE mermaid still draws Provider + optional Lifecycle as the provider layer, with prose that Connection embeds faces — diagram lags Connection-first wording slightly *(comfydesk 2026-09-27 systems map)*.

### What's redundant now that Connection exists

| Legacy path | Connection equivalent |
|-------------|------------------------|
| OAI Compatible + Lifecycle LM Studio | Connection host LM Studio / Auto + `ttl` / `context_length` face |
| OAI Compatible + Lifecycle Textgen | Connection Textgen face + `manage_model_memory` |
| Textgen Provider + embedded memory toggle | Connection Textgen face |
| Separate `/models/oai-compat` + `/detect` UX | `/models/connection` + host_mode |

Legacy nodes remain registered only long enough to keep old workflows working and confirm the Connection path (`README` Legacy section); then unregister/hide them. New graphs should not need Provider+Lifecycle pairs.

### Shared under the hood

All providers still produce the same **`LLM_PROVIDER`** shape and call the single **`oai_compat`** adapter (`adapters/oai_compat.py`). Generation, allowlists, Textgen load/unload, LM Studio TTL/load/unload, and cancel polling are one path. Dual *nodes* ≠ dual *adapters*.

---

## 3. Conflicts / debt (cite in-repo; don't invent)

### Dual provider story (A-25, feedback 2026-06-17)

Three ways to say "talk to Textgen": Connection Textgen face, Textgen Provider, or OAI Compatible URL pointed at Textgen (+ optional Lifecycle). Lifecycle sockets only attach to OAI Compatible; Textgen Provider already embeds the same toggle. Tracker: A-25 Unresolved → D-2 rethink. Connection docs lead demoted legacy in README/CODEBASE but did not remove nodes.

### VRAM control direction (Q2 answered)

Vir settled 2026-09-28: for new graphs, **Connection owns VRAM** through one user-facing **Manage VRAM / Manage memory** toggle. The backend is detected or pinned, and the pack sends the appropriate backend-specific commands: Textgen and LM Studio keep their existing API paths under the same toggle metaphor. There are no separate Lifecycle controls for new work and no extra knobs that do not apply.

llama.cpp is setup-gated, not universal: expose/use VRAM management only when the host exposes router `/models/load` and `/models/unload`. If those routes are absent, chat still works; the toggle is hidden/inert and status should make the limitation clear.

This resolves the product direction, but **does not greenlight implementation** of the unified toggle or an unrelated overhaul. Code changes remain ask-first.

The current surfaces below are therefore a compatibility snapshot, not three competing new-graph controls:

| Current surface | Existing behavior | New-graph direction |
|-----------------|-------------------|---------------------|
| **1. Connection** | Existing backend-specific lifecycle behavior | Canonical single VRAM toggle |
| **2. Lifecycle → OAI** | Separate Lifecycle nodes → `LLM_LIFECYCLE` → OAI Compatible `lifecycle` input | Legacy/compatibility only; no revival for new work |
| **3. Textgen-on-provider** | Textgen Provider's on-node `manage_model_memory` | Legacy/compatibility only; Connection owns new-graph control |
### Code-voice lag (OAI vs Connection)

*(Provenance: comfydesk 2026-09-27 systems map.)*

When OAI Compatible fingerprints Textgen, docstring/log still prefers the **Textgen provider**. README + Connection DESCRIPTION prefer **Connection** for new graphs. Users following code hints diverge from the docs lead until strings catch up. *Hypothesis only — not a string-edit task in this note.*

### Options walls (height ≠ existence)

Tall toggle nodes (qol-backlog: evaluate Textgen / LM Studio height). Worklist **defers** Options height polish until systems direction says Options stay. Split vs keep vs fold into Advanced/Connection is open (see §4). `options_in` merge exists in helper but is unused by node INPUT_TYPES - latent API, not a user-facing chain today.

**Stay/go evidence — not accidental debt** *(comfydesk 2026-09-27 systems map):*

- **A-1 Decided:** per-provider Options + enable toggles (omit when OFF).
- **A-13 Decided:** Basic = compact inline params; Advanced = modular provider/options/meta.
- design_review shipped single Options walls then evaluate height — **height is polish, not existence**.

So "Options might go away" in §4 is a *product* hypothesis about the spine, not evidence that separate Options were a mistake. Do **not** promote height polish from this map.

### Auth / status uneven

- Keys: config/env only; OAI-shaped fallback via `providers.oai_compat`; Textgen dual api/admin keys (`get_textgen_auth_keys`) - documented in README / `textgen-lifecycle-verified.md`.
- Status chrome: Connection has richer face (detected/effective/loaded/auth hint). Legacy providers use `model_dropdown.js` status widgets (P-12 fixed). Headless/API mode: `/llm-bikeshed/*` client routes **not** API-mode compatible; generation still works from baked URL/model in graph JSON (`CODEBASE`).
- No browser set-key / reload-config in normal user path (tracker once mentioned reload endpoint; product still "edit yaml + restart ComfyUI" in README).

### `model` vs `loaded_model` (selector vs status) - known smell

*(Provenance: 2026-09-28 dig; Vir complaint. **NOT greenlit** in isolation - same banner as this note.)*

Two different things that look like "the model":

| Widget / field | Role | Where it lives |
|----------------|------|----------------|
| **`model`** | **Request identity** | Always becomes `LLM_PROVIDER["model"]` -> payload `"model"` in `oai_compat` generate. `VALIDATE_INPUTS` requires it. |
| **`loaded_model`** | **Status chrome only** | JS-only, `serialize:false`; never enters the provider dict. Refresh updates status; it does **not** copy into `model`. |

**Observed mismatch (local / single-slot):** external llama.cpp load -> status line can show the newly loaded name, but the request still uses the stale combo `model` until the user changes the combo by hand. The combo does **not** load/unload weights by itself.

**Why it is not total accident:** deliberate for OpenAI / multi-model hosts (pick which id to call while something else may be "loaded" elsewhere). **Debt** for single-slot local hosts where "what's loaded" and "what we will call" should usually match.

**Path nuance:** Connection llama.cpp (`catalog=False`) returns `loaded_model` None - the correct `loaded:` line after an external swap is typically the **OAI Compatible** path, not Connection's llama.cpp face.

**Ownership (honesty, not a ship plan):** there is **no greenlit overhaul** yet. Vir: feels like slop unless an overhaul makes the split irrelevant. So either (a) a future Connection/provider overhaul **owns killing** this dual surface, or (b) we later schedule a **small local-host follow** (auto-follow / use-loaded / warn / omit-when-single) - not leave it unlabeled forever. *Do not implement either from this note.*

### `ensure_load_on_select` policy

Connection widget default **OFF**; URL changes never load; model-dropdown change may POST ensure-loaded when ON (`CODEBASE` / `llm_connection.js`). Python `build_provider` marks the flag UI-only (`ARG002`) - does **not** enter `LLM_PROVIDER`. Load-at-queue still driven by `load_before_generate` + lifecycle inside the adapter. Policy surface is frontend + ensure-loaded route, not the provider dict.

### Cancel / VRAM gaps (documented)

From [`cancel-interrupt-status.md`](cancel-interrupt-status.md):

- ComfyUI Cancel **unblocks** the execution thread (interruptible HTTP) for generation/lifecycle GETs used that way.
- **Textgen:** host stop via `POST /v1/internal/stop-generation` - empirical PASS (v4.9, 2026-06-17).
- **LM Studio:** no stop API in pack - empirical FAIL/expected (v0.4.16); inference can continue after Cancel.
- **No unload-on-interrupt:** successful-path unload only; interrupt can leave model loaded (product choice unresolved).
- Lifecycle chain empirical QA (A-15 / A-18 / A-19 / A-22) still open; worklist defers behind systems direction.

VRAM sharing intent remains core (`CODEBASE` purpose; concept doc A-15/A-18): Textgen explicit load/unload; LM Studio TTL (+ explicit load for context - JIT #1463 still open per lm-studio research note).

---

## 4. Keep / demote / kill - *hypotheses* (not recommendations to ship)

Label: **hypothesis**. Ask Vir before any overhaul.

| Surface | Hypothesis | Notes |
|---------|------------|--------|
| **LLM Connection** | **Keep** as primary connectivity | Already documented lead (`2be26be`). |
| **OAI Compatible provider** | **Compatibility/test path until Connection is confirmed** | Keep existing workflows working; then unregister/hide rather than maintain a second product. |
| **Textgen provider** | **Compatibility/test path until Connection is confirmed** | Keep existing workflows working; then unregister/hide rather than maintain a second product. |
| **Lifecycle nodes** | **Demote** for new graphs; retain for legacy/compatibility | No revival for new work; Connection owns the single VRAM toggle. |
| **Generate Basic + Advanced** | **Keep** split for now (A-13 decided) | *Hypothesis:* someday one node with optional breakouts - not proposed here. A-13 is evidence the split was intentional, not debt. |
| **Options nodes** | **Open - might go away, merge, or stay** | A-1/A-13 decided separate Options + Basic/Advanced — **not** accidental debt; height ≠ existence *(comfydesk 2026-09-27)*. Alternatives (*hypotheses*): fold common knobs into Advanced; single Options with backend allowlist; keep toggles but split/collapse UI. **Do not implement Options polish until this is answered** (worklist). |
| **Preset / Load Text** | **Keep** | Independent STRING utilities. |
| **Socket types** | **Keep** `PROVIDER` / `OPTIONS` / `META`; **`LIFECYCLE` may shrink** if Connection-only world wins | *Hypothesis:* lifecycle becomes fields-only inside PROVIDER (already true on Connection). |

---

## 5. Open questions for Vir (product choices - not height polish)

1. **Canonical connectivity — ANSWERED (Vir, 2026-09-28):** Connection is the new path. Keep legacy providers only for compatibility/testing and to avoid breaking existing workflows; as soon as Connection is confirmed to work, unregister/hide them. They are not a second maintained product.
2. **Lifecycle mental model — ANSWERED (Vir, 2026-09-28):** Keep backend-specific VRAM controls as face knobs on Connection. When the selected host/backend does not support load/unload, disable the **Manage model memory** toggle and/or surface a clear unsupported/error status; never leave a dead switch. Legacy Lifecycle nodes remain only for compatibility while the Connection path is confirmed (Q1).
3. **Options future:** Keep per-backend Options nodes, merge into Advanced/Connection, or replace with a thinner sampling surface? (Height polish blocked on this.)
4. **Basic vs Advanced:** Keep two generate nodes, or converge once Options direction is clear?
5. **Interrupt + VRAM policy:** On Cancel, should Textgen/LM Studio **unload**, leave loaded, or defer - and is LM Studio "Cancel doesn't stop GPU" acceptable as documented limit?
6. **`ensure_load_on_select`:** Stay default OFF forever, or become part of a clearer "when does the pack load weights?" story with Manage model memory?
7. **Auth UX:** Stay yaml/env + restart only, or invest in status/reload so Connection's auth hint is actionable without doc diving?
8. **llama.cpp:** Connection/OAI `/v1` forever enough, or revisit dedicated node later (D-4 still tabled)?
9. **OpenAI / cloud knobs:** Stay first-class on Connection host_mode + Options OpenAI (A-23), or demote cloud surfaces while leaving nodes loadable? *(comfydesk 2026-09-27 systems map)*
10. **Example / docs truth:** Bring `advanced_with_options.json` (and CODEBASE mermaid if any) onto the **Connection → Options → Advanced** spine so examples match the recommended composition? *(comfydesk 2026-09-27 systems map)*
11. **`model` vs `loaded_model`:** Overhaul kills the dual surface, or schedule a small local-host fix (auto-follow / use-loaded / warn / omit-when-single)? Unlabeled forever is not OK - Vir 2026-09-28. *(2026-09-28 dig; **not** greenlit alone)*

---

## 6. Non-goals of this note

- No ComfyUI **V3** node API spike  
- No Comfy Registry / publish changes  
- No implementing Options split, height collapse, or provider deletion  
- No resolving D-2 / A-25 in code - only framing for Vir  
- No promoting Options height polish from stay/go evidence  

---

## Quick diagram (mental model)

```text
                    ┌─ (legacy) Lifecycle ─┐
                    │                      ▼
 Connection ──┐     │              OAI Compatible ──┐
 Textgen Prov.┼─────┴───────────────────────────────┤
                │         LLM_PROVIDER              ▼
                └─────────────────────────────────► Generate Basic
 Options* ──LLM_OPTIONS───────────────────────────► Generate Advanced
                                                    │
                                              LLM_META chain
                                                    ▼
                                              Generate …
```

Adapter underneath: always `oai_compat` → `POST {url}/v1/chat/completions` (+ Textgen `/v1/internal/model/*`, LM Studio TTL / `/api/v1/models/*` when lifecycle present).

---

## Related worklist

Live queue: [`WORKLIST.md`](../../WORKLIST.md) - systems map item points here (folded comfydesk deltas 2026-09-27; `model`/`loaded_model` smell 2026-09-28; Vir Q2 lifecycle/VRAM lock 2026-09-28); Options height remains deferred until Vir answers section 5 item 3 (and related spine questions 9-11).
