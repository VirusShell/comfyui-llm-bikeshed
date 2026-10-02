# Pack systems map (pre-overhaul)

**Date:** 2026-09-27  
**Status (honesty scrub 2026-09-28, pack tip `b61be6b` / v1.1.0):** The **overhaul is still not greenlit** (Options merge/delete, node unregister, Q11 sync). The ask-first archive delete of superseded docs landed after this note (CHANGELOG [Unreleased]). This note is orientation, not the live queue ([`WORKLIST.md`](../../WORKLIST.md)) and not a ship plan. Shipped since the original "NOT greenlit" banner: Q6 (no select-preload), A-25 (Manage VRAM; OFF does not embed a lifecycle), Q5 (`unload_on_interrupt`), Q4/Q9/`max_tokens`, and DOC-3 (Connection → Advanced). Options height polish stays deferred. Vir Q1 is answered: legacy providers remain only for compatibility/testing and existing workflows until the Connection path is confirmed; then unregister/hide them. This does **not** greenlight unrelated overhaul code.
**Vir Q2 (Lifecycle / VRAM) is answered (2026-09-28):** For new graphs, Connection owns VRAM through one user-facing **Manage VRAM / Manage memory** toggle. The backend may be detected or pinned; the pack sends the backend-appropriate load/unload/TTL commands. Textgen and LM Studio keep their existing API paths under that single-toggle metaphor. llama.cpp VRAM management is setup-gated: only when the host exposes router `/models/load` and `/models/unload`; otherwise chat still works and the toggle is hidden/inert with status.
**A-25 / D-2 shipped (2026-09-28):** Connection `manage_model_memory` (default ON) is that toggle. Textgen ON loads before generate and unloads after the chain; OFF does neither. LM Studio ON keeps TTL and `context_length` on load; OFF embeds no lifecycle, so the pack does not load, set TTL, or unload. llama.cpp stays chat-only with the toggle hidden: `detection.py` does not probe router `/models/load` + `/models/unload`, and the adapter has no llama.cpp unload. This does not greenlight Options merge, node deletes, Q11 sync, or a new llama.cpp router client.
**Vir Q3-Q7 (Options, generate shape, interrupt policy, preload, and Auth UX) are answered (2026-09-28):** the docs direction is thin/no separate Options, one Generate node shaped like current Advanced, interrupt/unload policy in node Properties rather than main widgets, no model-pick preload, and off-graph auth with reload via Refresh Node Definitions/config reload rather than a full restart. Q6 preload is implemented. Q4/Q5 code landed (see shipped note below). Options merge/delete and Q7 auth UX are still not implemented.
**Vir Q8-Q10 + max_tokens (2026-09-28):** Connection/OAI `/v1` is enough for llama.cpp — dedicated node is dead (D-4 closed). OpenAI/cloud knobs: keep current host guidance + legacy; prefer `max_completion_tokens` for new OpenAI paths, keep `max_tokens` for legacy; send `seed` when set; **no** strip-on-cloud; **no** native Anthropic. `max_tokens` is **output-only**; generous values allowed; `0` = omit / host default (send when ≥1); no artificial prompt caps; user owns OOM/timeout. Q9 and the `0` widget floor are implemented (see shipped note). **DOC-3 landed:** README, CODEBASE, and `example_workflows/connection_generate.json` lead with Connection → Advanced Generate and do not put Options on that path. Basic / Options / Provider / Lifecycle stay registered and are labeled legacy.
**Q4 / Q5 / Q9 / max_tokens shipped (2026-09-28):** Both Generate class IDs stay registered. **LLM Generate (Advanced)** is the intended spine (optional provider / options / meta, face `max_tokens` above `seed`, default 1024, min 0). Temperature was not added to Advanced. Basic keeps temperature / max_tokens / seed and the same min 0. Face `0` omits the face cap and keeps Options/meta limits; `>= 1` sends (`max_completion_tokens` for backend `openai`, `max_tokens` otherwise). Options `max_tokens` still sends `max_tokens`. Seed is sent when set, including 0. No cloud strip. No native Anthropic. Interrupt unload is LiteGraph property `unload_on_interrupt` (right-click Properties, default off), read from `extra_pnginfo.workflow`. It unloads only when a lifecycle is embedded (Manage VRAM ON or legacy lifecycle). API prompts without that blob stay off. Options nodes were not deleted; their token widgets allow 0.
**Vir Q11 (`model` vs `loaded_model`) — findings landed, not implemented (2026-09-30):** [`r1-q11-model-vs-loaded.md`](r1-q11-model-vs-loaded.md) (pack `db7eb48`). Select-always: the graph `model` is what generate sends. Loaded→default on local hosts is a future design and stays ask-first. The 2026-09-28 note is superseded. Do **not** implement sync. See WORKLIST R-1.
**Scope:** Connection, legacy providers, lifecycle, generate, options, utils, socket types - composition, overlap, debt.  
**Non-goals of the original note:** No V3 spike, no registry work, no Options merge/delete, no Basic/Advanced unregister, no dedicated llama.cpp node, no strip-on-cloud, no native Anthropic, no naive model/loaded sync. Q6 preload, A-25 Manage VRAM, and Q4/Q5/Q9/`max_tokens` later shipped (header). This note is still not a license for Options delete, node unregister, or Q11 sync.

**Pack tip:** the original fold cited `f91eec4` (Vir Q3–Q7). The comfydesk note was written against pack tip `7ad0758`. **Honesty-scrub tip: `b61be6b` (v1.1.0).** The overhaul is still not greenlit. Q6, A-25, Q5, Q4/Q9/`max_tokens`, and DOC-3 are shipped on that tip.

**External provenance:** comfydesk systems map — `D:\ai\bot-grok\comfydesk\notes\2026-09-27-bikeshed-systems-map.md` (cite below as **“comfydesk 2026-09-27 systems map”**). Pack structure kept; their deltas folded in.

Sources (cite, don't re-invent): [`CODEBASE.md`](../../CODEBASE.md), [`README.md`](../../README.md), [`docs/text_gen_processing_concept.md`](../text_gen_processing_concept.md), [`docs/resolution_tracker.md`](../resolution_tracker.md) (A-1, A-13, A-25, D-2, A-15/A-18/A-22), [`docs/proposals/product-direction-and-scope.md`](../proposals/product-direction-and-scope.md), [`docs/research/cancel-interrupt-status.md`](cancel-interrupt-status.md), [`docs/research/textgen-lifecycle-verified.md`](textgen-lifecycle-verified.md), [`docs/research/lm-studio-lifecycle-verified.md`](lm-studio-lifecycle-verified.md), [`docs/research/user-feedback-2026-06-17.md`](user-feedback-2026-06-17.md), Connection docs lead `2be26be`, worklist `7ad0758` / `6a0dc86`, **comfydesk 2026-09-27 systems map**, **2026-09-28 dig** (`model` vs `loaded_model` selector/status). The QoL backlog file was removed in the honesty cleanup; deferred height items live on WORKLIST.

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

**Intended new-graph spine:** **Connection  ->  LLM Generate (Advanced).** Shipped face knob is `max_tokens` above `seed` (temperature was not added; it stays on legacy Basic or Options). Leave the rest to host defaults. No separate Options node is part of this intended spine. Connection owns new-graph VRAM management through one backend-adaptive **Manage VRAM / Manage memory** toggle; Textgen and LM Studio retain their existing API paths behind it. llama.cpp only gets VRAM management when its host exposes router `/models/load` and `/models/unload`; otherwise chat remains available and the toggle is hidden/inert with status. Interrupt/unload policy is an additional node Properties option, not a main-face widget, and must respect Manage VRAM. No model-pick preload: load only on generate or when Manage VRAM needs it. Legacy Provider + Lifecycle still emit the same `LLM_PROVIDER` shape and remain temporarily registered for compatibility/testing and existing workflows while the Connection path is confirmed; then unregister/hide them rather than maintain a second product.

The old VRAM split is resolved directionally for new graphs: one Connection toggle, with backend-specific API behavior behind it; the separate Lifecycle path remains legacy/compatibility only. Vir Q3-Q7 are settled: no separate Options node in the new-graph spine, one Advanced-shaped Generate node with only average-user knobs, interrupt/unload policy in node Properties, and no ensure_load_on_select/model-pick preload (Q6 implemented). Q4/Q5/Q9/max_tokens code shipped (header note): Advanced is that spine, both nodes stay registered, `max_tokens` min is 0, OpenAI face uses `max_completion_tokens`, interrupt unload is property `unload_on_interrupt` and respects Manage VRAM. DOC-3 wrote that spine into README, examples, and CODEBASE. Options merge, Generate unregister, and Q11 sync remain ask-first. Q11 findings are in [`r1-q11-model-vs-loaded.md`](r1-q11-model-vs-loaded.md); select-always stands, and loaded→default is not implemented. The A-25 / D-2 Manage VRAM toggle is shipped for Textgen and LM Studio.

---

## 1. Job of each surface

Plain-language "what is this node *for*" - not a full widget catalog.

### LLM Connection (`LLMConnection`) - **recommended entry**

One adaptive node: host mode (Auto or pin LM Studio / Textgen / llama.cpp / OpenAI / Generic), URL + model, and one user-facing **Manage VRAM / Manage memory** toggle for new graphs. The backend may be detected or pinned; the pack sends the appropriate load/unload/TTL commands. Textgen and LM Studio keep their existing API paths behind the toggle. llama.cpp VRAM management is setup-gated: only use/show it when the host exposes router `/models/load` and `/models/unload`; otherwise chat still works and the toggle is hidden/inert with status. Shipped face: LM Studio still shows `ttl` and `context_length` while Manage VRAM is ON; other faces do not add lifecycle knobs. No model-pick preload or `ensure_load_on_select`: load only when generation runs or Manage VRAM needs it. Outputs **`LLM_PROVIDER`**. No API-key widgets. Status chrome + Refresh Models via `POST /llm-bikeshed/models/connection`. Prefer this over Provider + Lifecycle for new graphs (`README`, `CODEBASE`, `2be26be`).

### Legacy: LLM Provider OAI Compatible (`LLMProviderOAICompat`)

Fingerprints backend at URL; optional **`LLM_LIFECYCLE`** input. Models via `/llm-bikeshed/models/oai-compat`. Still registered for migrated graphs and for llama.cpp `/v1` when the graph is not using Connection. Hint-logs when detected backend is Textgen ("prefer Textgen provider"). Sets `load_before_generate` True when backend is Textgen even without lifecycle (unload still lifecycle-gated).

**Code-voice lag** *(comfydesk 2026-09-27 systems map):* OAI Compatible docstring/log still steers Textgen fingerprints toward the **Textgen provider**, while README / Connection lead prefer **Connection** for new graphs. Dual product voice until docs/code strings align.

### Legacy: LLM Provider Textgen (`LLMProviderTextGenWebUI`)

Textgen-only URL/defaults; no fingerprinting; models via `/llm-bikeshed/models/textgen`. Its on-node memory control is a compatibility path only; for new Textgen graphs, Connection owns the single VRAM toggle. Keep this provider for existing workflows while the Connection path is confirmed.

### Lifecycle: LM Studio / Textgen (`LLMLifecycle*`)

Output **`LLM_LIFECYCLE`** only. These nodes remain the legacy/compatibility path: wire into **OAI Compatible's** `lifecycle` input, not into Connection. They are not being revived for new graphs; Connection owns the single VRAM toggle there. Existing LM Studio (`ttl` / `context_length`) and Textgen (`manage_model_memory`) API behavior remains available behind the Connection metaphor. The Connection toggle itself shipped (A-25 / D-2); unregistering these nodes is still escalate/registry.

### Generate Basic / Advanced (both still registered)

Basic is compact: `provider` + prompt/system + inline temperature / max_tokens / seed. Returns `(text, LLM_META)`. Always re-runs (`IS_CHANGED`  ->  NaN). Sets `skip_unload` via graph introspection when another gen node is downstream on `meta` (A-15 / P-10). **Q4 shipped without unregistering either class.** Advanced is the intended spine.

### Advanced shape (`LLMGenerateAdvanced`) — intended spine

Modular: optional `provider`, optional **`LLM_OPTIONS`**, optional upstream **`LLM_META`**. Explicit provider/options override meta. Same meta out + `skip_unload` behavior. Seed always applied. Face `max_tokens` sits above `seed` (min 0, default 1024). Temperature was not added (still Basic or Options). `0` omits the face cap and keeps an Options/meta limit; `>= 1` replaces it.

### Options: LM Studio / OpenAI / Textgen (`LLMOptions*`)

Current Options nodes provide per-backend sampling params with enable toggles; only ON params enter the dict (`options_base.build_toggle_options`). They are not part of the intended new-graph spine: Vir Q3 says probably no separate Options node; at most expose average-user knobs on Generate and leave the rest to host defaults.

### Utilities: Preset Loader / Load Text File

STRING sources for `system_prompt` / `prompt`. Presets from pack `presets/`; Load Text from ComfyUI input folder. Separate from provider/options story (A-6).

### Socket types (plain dicts, string type names)

| Socket | Typical contents | Flows |
|--------|------------------|--------|
| **`LLM_PROVIDER`** | `backend`, `adapter` (`oai_compat`), `url`, `model`, `timeout`, optional `lifecycle`, `load_before_generate` | Connection / Providers → Generate |
| **`LLM_LIFECYCLE`** | `{type: lm_studio\|text_gen_webui, …}` | Lifecycle → OAI Compatible only (legacy) |
| **`LLM_OPTIONS`** | Toggle-selected sampling keys | Options -> Advanced (current/legacy) |
| **`LLM_META`** | `{provider: public_provider(...), options}` - **no secrets** | Gen → Gen chaining; Advanced can ingest |

Secrets never live in these dicts; adapters resolve keys at HTTP time (`config.auth`).

---

## 2. How they compose

### Typical graphs (today)

```text
A) Intended new graph (shipped example: connection_generate.json)
   LLM Connection  --LLM_PROVIDER-->  LLM Generate (Advanced)  --> text
                                              \--> LLM_META (optional chain)
   Face max_tokens above seed. No Options node. Manage VRAM on Connection.

B) Legacy Options graph (still loads; not the intended path)
   Connection or Provider --> Advanced
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
| `example_workflows/connection_generate.json` | Connection + Generate Advanced | **A** (docs lead) |
| `connection_basic.json` | Connection + Generate Basic | Legacy Basic on Connection |
| `basic_generation.json` | OAI Compatible + Generate Basic | **C**-shaped without Lifecycle |
| `textgen_basic.json` | Textgen provider + Generate Basic | **D** |
| `advanced_with_options.json` | OAI Compatible + Options LM Studio + Generate Advanced | **B** with **legacy** provider |

**Not in examples today:** Lifecycle nodes; Connection + Options + Advanced (not the intended spine); meta-chain graphs; OpenAI Options; Textgen Options.

**Vir Q10 / DOC-3 (2026-09-28):** README, examples, and CODEBASE lead with **Connection → Advanced Generate**. No Options node on that path. CODEBASE's data-flow diagram matches that spine. Options merge and node unregister stay escalate.

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

### Dual provider story (A-25, feedback 2026-06-17) - legacy compatibility
Three ways to say "talk to Textgen" remain in the compatibility snapshot: Connection Textgen face, Textgen Provider, or OAI Compatible URL pointed at Textgen (+ optional Lifecycle). For new graphs, Connection is canonical and owns the single VRAM toggle; the other paths remain only for compatibility/testing and existing workflows while Connection is confirmed. **Q2 is settled; this is not a green light for code.**

### VRAM control direction (Q2 answered)

Vir settled 2026-09-28: for new graphs, **Connection owns VRAM** through one user-facing **Manage VRAM / Manage memory** toggle. The backend is detected or pinned, and the pack sends the appropriate backend-specific commands: Textgen and LM Studio keep their existing API paths under the same toggle metaphor. There are no separate Lifecycle controls for new work and no extra knobs that do not apply.

llama.cpp is setup-gated, not universal: expose/use VRAM management only when the host exposes router `/models/load` and `/models/unload`. If those routes are absent, chat still works; the toggle is hidden/inert and status should make the limitation clear.

**Shipped:** the unified toggle is on Connection for Textgen and LM Studio. llama.cpp is the hidden/inert case in this tree, because those router routes are not verified in detection or the adapter. Legacy Lifecycle nodes remain registered. Unrelated overhaul (Options merge, node deletes, Q11) stays ask-first.

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

Historical/current toggle nodes are tall (WORKLIST Deferred: evaluate Textgen / LM Studio height). Vir Q3 settles the product direction: probably no separate Options node in the intended new-graph spine; at most expose average-user knobs on Generate and leave the rest to host defaults. Options height is therefore not a greenlit implementation task.

**Historical stay/go evidence (superseded by the Vir Q3 docs direction; not an implementation green light)**

- **A-1 Decided:** per-provider Options + enable toggles (omit when OFF).
- **A-13 historical decision:**
- design_review shipped single Options walls then evaluate height — **height is polish, not existence**.

So "Options might go away" is now Vir Q3's settled docs direction for the intended spine, not evidence that implementation may start. Keep current nodes for compatibility until an explicit code task; do not promote height polish or merge/delete work from this map.

### Auth / status uneven

- Keys: config/env only; OAI-shaped fallback via `providers.oai_compat`; Textgen dual api/admin keys (`get_textgen_auth_keys`) - documented in README / `textgen-lifecycle-verified.md`.
- Status chrome: Connection has richer face (detected/effective/loaded/auth hint). Legacy providers use `model_dropdown.js` status widgets (P-12 fixed). Headless/API mode: `/llm-bikeshed/*` client routes **not** API-mode compatible; generation still works from baked URL/model in graph JSON (`CODEBASE`).
- **Vir Q7 (2026-09-28):** auth keys stay off-graph in config/env. A wrong key must fail generation loudly with a clear auth flag/status. After key/settings updates, use Refresh Node Definitions (and/or config reload) as the happy path; do not require a full Comfy restart. This is docs-only and does not greenlight auth/reload implementation.

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

**Ownership (honesty, not a ship plan):** there is **no greenlit overhaul** yet. Current evidence is [`r1-q11-model-vs-loaded.md`](r1-q11-model-vs-loaded.md). Select-always stands. Loaded→default on local hosts is a future design, not this map. *Do not implement sync from this note.*

### Model-pick preload policy (Q6 answered)

**Vir Q6 (2026-09-28):** no `ensure_load_on_select` and no preload on model pick. Loading happens only when a generate run requires it or when the Manage VRAM policy needs it; changing the model selection must not load weights. Implemented: widget removed; Connection + legacy provider JS no longer ensure-load on model pick; `POST /llm-bikeshed/models/ensure-loaded` kept for generate / Manage VRAM callers.

### llama.cpp surface (Q8 answered)

**Vir Q8 (2026-09-28):** Connection and OAI Compatible `/v1` are enough for llama.cpp. The dedicated llama.cpp / llama-server node is **dead** — D-4 closed (was tabled; now rejected). Router `/models/load` + `/models/unload` remain the VRAM setup gate from Q2; chat without those routes still works. **Docs lock only; no node deletion/registration work greenlit here beyond the product decision.**

### OpenAI / cloud knobs (Q9 answered)

**Vir Q9 (2026-09-28) — implemented:** stay with current host guidance plus legacy paths. The Generate face writes `max_completion_tokens` when `backend` is `openai`, and `max_tokens` otherwise. A lone Options `max_tokens` is still sent as `max_tokens`. If both fields are present, `max_completion_tokens` wins. `seed` is sent when set (including widget `0`). **No** strip-on-cloud. **No** native Anthropic.

### `max_tokens` semantics (Vir 2026-09-28)

- **Output-only** — caps completion length, not prompt+completion together.
- **Generous values allowed** — no pack-imposed artificial prompt/context caps; the user owns OOM and timeout risk.
- **`0` = omit / host default** — when the Generate face widget is 0, do not write a face token field (host default). On Advanced, an Options or meta limit already in the dict is kept. Send the field when ≥1. The adapter also drops `max_tokens` / `max_completion_tokens` when the value is below 1, so an enabled Options toggle set to 0 does not send `0`.
- **UI min is 0** on Generate and on Options token widgets (was 1). That is how omit-via-0 is entered. No separate “use host default” control.
- Applies to the intended Generate face and the legacy Options paths that still expose the knob.
- **Shipped** in the Generate face, Options mins, and `adapters/oai_compat.py`. No artificial prompt cap was added. User still owns OOM/timeout. The widget max stays 128000.

### `model` vs `loaded_model` (Q11 — findings landed; do not implement)

Smell section above remains. **2026-09-30:** evidence is [`r1-q11-model-vs-loaded.md`](r1-q11-model-vs-loaded.md). Select-always. A future loaded→default fill on local hosts is still ask-first. Always copying loaded over a saved selection is unsafe (see that note). *Do not implement sync from this note.*

### Cancel / VRAM gaps (documented)

From [`cancel-interrupt-status.md`](cancel-interrupt-status.md):

- ComfyUI Cancel **unblocks** the execution thread (interruptible HTTP) for generation/lifecycle GETs used that way.
- **Textgen:** host stop via `POST /v1/internal/stop-generation` - empirical PASS (v4.9, 2026-06-17).
- **LM Studio:** no stop API in pack - empirical FAIL/expected (v0.4.16); inference can continue after Cancel.
- **Unload-on-interrupt (Q5 shipped):** default is still successful-path unload only. Right-click Properties `unload_on_interrupt` (default off) unloads on Cancel when a lifecycle is embedded. Manage VRAM OFF embeds no lifecycle, so the property cannot unload. It is not a face widget. API prompts without `extra_pnginfo.workflow` keep the default off.
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
| **Generate Basic + Advanced** | **Advanced is the intended spine; both stay registered** | Q4 shipped: `max_tokens` above `seed` on Advanced; min 0. Temperature not added to Advanced. Unregister/collapse is still escalate. |
| **Options nodes** | **Probably remove from the intended new-graph spine** | Vir Q3: at most expose average-user knobs (likely temperature and `max_tokens`) on Generate; leave the rest to host defaults. Existing Options nodes remain a compatibility snapshot. **No merge/delete is greenlit here.** |
| **Dedicated llama.cpp node** | **Kill (D-4 closed)** | Vir Q8: Connection/OAI `/v1` enough; no dedicated llama-server node. |
| **Preset / Load Text** | **Keep** | Independent STRING utilities. |
| **Socket types** | **Keep** `PROVIDER` / `OPTIONS` / `META`; **`LIFECYCLE` may shrink** if Connection-only world wins | *Hypothesis:* lifecycle becomes fields-only inside PROVIDER (already true on Connection). |

---

## 5. Open questions for Vir (product choices - not height polish)

1. **Canonical connectivity — ANSWERED (Vir, 2026-09-28):** Connection is the new path. Keep legacy providers only for compatibility/testing and to avoid breaking existing workflows; as soon as Connection is confirmed to work, unregister/hide them. They are not a second maintained product.
2. **Lifecycle / VRAM mental model - ANSWERED + toggle shipped (Vir, 2026-09-28; A-25 / D-2):** Connection owns new-graph VRAM through one backend-adaptive Manage VRAM / Manage memory toggle; separate Lifecycle nodes are legacy/compatibility only. Textgen and LM Studio keep their existing API paths behind the toggle. llama.cpp management is setup-gated on router `/models/load` + `/models/unload`; those routes are not verified here, so the toggle stays hidden and chat still works.
3. **Options future - ANSWERED (Vir, 2026-09-28):** Probably no separate Options node. At most expose average-user knobs users care about (likely `max_tokens`, maybe temperature) on Generate; leave the rest to host defaults. **Docs lock only; do not merge/delete Options yet.**
4. **Basic vs Advanced - ANSWERED + face shipped (Vir, 2026-09-28):** One intended Generate, shaped like Advanced, with `max_tokens` above `seed`. Both class IDs stay registered.
5. **Interrupt + VRAM policy - ANSWERED + property shipped (Vir, 2026-09-28):** Respect Manage VRAM. `unload_on_interrupt` is a right-click Properties flag, default off, not a face widget. No lifecycle (Manage VRAM OFF) means no unload.
6. **Model-pick preload - ANSWERED + IMPLEMENTED (Vir, 2026-09-28):** No `ensure_load_on_select` and no preload on model pick. Load only when a generate run requires it or Manage VRAM needs it. Widget + select-triggered JS paths removed; ensure-loaded route retained for generate/VRAM.
7. **Auth UX - ANSWERED (Vir, 2026-09-28):** Keys stay off-graph in config/env; wrong key fails generation loudly with a clear auth flag/status. After key/settings updates, Refresh Node Definitions (and/or config reload) is the happy path, not a full Comfy restart. **Docs lock only; no implementation green light.**
8. **llama.cpp - ANSWERED (Vir, 2026-09-28):** Connection/OAI `/v1` is enough. Dedicated llama.cpp / llama-server node is dead; **D-4 closed**. **Docs lock only.**
9. **OpenAI / cloud knobs - ANSWERED + payload shipped (Vir, 2026-09-28):** Prefer `max_completion_tokens` for the Generate face when backend is OpenAI; keep `max_tokens` for legacy hosts and the Options `max_tokens` toggle; send `seed` when set; **no** strip-on-cloud; **no** native Anthropic.
10. **Example / docs truth - ANSWERED + DOC-3 written (Vir, 2026-09-28):** README / examples / CODEBASE lead with Connection → one Generate (Advanced). No separate Options node on the intended path. Example: `connection_generate.json`. Node unregister and Options merge stay escalate.
11. **`model` vs `loaded_model` — findings landed, not implemented (2026-09-30):** [`r1-q11-model-vs-loaded.md`](r1-q11-model-vs-loaded.md). Select-always. Loaded→default stays ask-first. WORKLIST R-1. *(**not** greenlit — no sync implementation)*

---

## 6. Non-goals of this note

- No ComfyUI **V3** node API spike  
- No Comfy Registry / publish changes  
- No Options merge/delete, Basic/Advanced unregister, auth/reload UX, provider deletion, dedicated llama.cpp node, strip-on-cloud, or native Anthropic. Q4/Q5/Q9 face, property, and payload work shipped later (header); this section does not reopen them.
- A-25 / D-2 Connection toggle is shipped; this note is not a license for Options merge, node deletes, or a llama.cpp router client
- No promoting Options height polish from stay/go evidence  
- No naive `model`/`loaded_model` sync; current Q11 note is `r1-q11-model-vs-loaded.md` (no sync implementation)  
- No version bump or unrelated code from this fold  

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

Live queue: [`WORKLIST.md`](../../WORKLIST.md) - systems map item points here (folded comfydesk deltas 2026-09-27; `model`/`loaded_model` smell 2026-09-28; Vir Q2—Q10 docs locks + max_tokens semantics 2026-09-28; Q11 findings 2026-09-30 (`r1-q11-model-vs-loaded.md`); Vir authorized implementing settled Q1–Q10 locks with escalate for publish/registry/deletes/credentials); Options height and merge/delete work remain deferred/not greenlit; D-4 closed.
