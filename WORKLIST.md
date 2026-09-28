# Worklist - comfyui-llm-bikeshed

**Updated:** 2026-09-28 (Vir authorized implementing settled Q1–Q10/max_tokens locks; Q6 preload rip **landed**; **A-25 / D-2** Connection Manage VRAM toggle **landed** (llama.cpp router path not wired); **Generate / Properties / knobs (Q4–Q5, Q9, max_tokens) landed** — Advanced stays the intended spine, both Generate nodes stay registered, interrupt unload is a node property; Q11/R-1 research note started; still escalate publish/registry/deletes/credentials; Options merge/delete and height remain deferred; DOC-3 spine rewrite still open) - Ordered by what is reversible and documented. Older backlog docs (`docs/qol-backlog.md`, `docs/resolution_tracker.md`, proposals, CODEBASE open-design notes) remain **sources for candidates**, not the live queue. This file is the actionable queue.

Legend: `[ ]` todo / `[x]` done / `[~]` deferred (intentionally out of scope now)

---

## Implementable (direction locked — Vir 2026-09-28)

Direction for Q1–Q10 + max_tokens is locked; code/docs work may proceed under that lock. **Still escalate to Vir before:** publish, registry unregister/hide, node deletes, credential changes.

- [x] **First code stream: Q6 preload rip** — remove model-pick preload (`ensure_load_on_select`, JS `ensure-loaded` / `scheduleModelLoad` on combo change in `js/llm_connection.js` + `js/model_dropdown.js`, Connection face widget). Load only on generate or when Manage VRAM needs it. Via Build/PR.
- [x] **A-25 / D-2** — unified Connection VRAM toggle (`manage_model_memory`) for Textgen and LM Studio. llama.cpp stays hidden: router `/models/load` + `/models/unload` are not verified in detection/adapters. Legacy Provider and Lifecycle nodes stay registered.
- [x] **Generate / Properties / knobs (Q4–Q5, Q9, max_tokens)** — Advanced-shaped intended spine (`max_tokens` above `seed`, min 0); interrupt/unload is LiteGraph property `unload_on_interrupt` (default off, respects Manage VRAM); OpenAI face uses `max_completion_tokens`, legacy hosts and Options `max_tokens` stay `max_tokens`; seed sent when set; no strip-on-cloud. Basic and Advanced stay registered. Options not deleted. Temperature was not added to Advanced.
- [ ] **DOC-3** — README / examples / CODEBASE onto Connection → one Generate spine (Q10; no Options on intended path)

## Ask-first / escalate (do not start without Vir)

- [ ] **DOC-1** off-repo ComfyUI reference corpus disposition: vendor / drop / hybrid
- [ ] **DOC-2** locate or rewrite missing `comfyui-node-standards.md`
- [ ] **Q1 follow-through** — unregister/hide legacy Provider + Lifecycle after Connection path confirmed (**registry**)
- [ ] **Options merge/delete** — Q3 direction is thin/no Options on new-graph spine; merge/delete and height stay escalate/deferred (**deletes**)
- [ ] Publish / credential surface changes

## Research (not implementation)

- [ ] **R-1 / Q11** — `model` vs `loaded_model`: per-backend reality → common rule. Research note: [`docs/research/2026-09-28-model-vs-loaded-per-backend.md`](docs/research/2026-09-28-model-vs-loaded-per-backend.md). Accidental auto-default must not force extra model load/OOM. **Reject** naive “always sync combo to loaded on status.” Do **not** implement sync.

## Deferred (only after systems direction)

- [~] **LLM Options node / height** (Textgen 24 toggles / LM Studio 18) - Vir Q3 docs direction is probably no separate Options node; at most expose average-user knobs on Generate and leave the rest to host defaults. Keep current nodes for compatibility, but do not implement merge/delete or height polish until explicitly tasked.
- [~] Empirical lifecycle chain QA (A-15 / A-18 / A-19 / A-22); P-11 URL->model refresh; Cancel cleanup gap — same gate: after composition direction, or ask Vir
- [~] Inline preset dropdown on generation nodes (post-v1; A-6 / qol)
- [~] Chat nodes, Image Describe, Structured Output, extra cloud APIs (tracker tabled; CODEBASE open-design pointer only)
- [~] Cooperative interrupt for long llama.cpp reasoning without unloading the model (qol Future / research)

## Done (recent)

- [x] **Generate / Properties / knobs (Q4–Q5, Q9, max_tokens)** - **LLM Generate (Advanced)** is the intended spine: optional provider / options / meta, face `max_tokens` above `seed` (default 1024, min 0). Basic stays registered with the same min-0 cap (temperature already on Basic; not added to Advanced). `0` omits the face cap (Options/meta limits kept); `>= 1` sends. OpenAI face values go out as `max_completion_tokens`. Legacy hosts and an Options `max_tokens` toggle still send `max_tokens`. Seed is sent when set, including 0. No cloud strip. No native Anthropic. Right-click Properties `unload_on_interrupt` (default off) unloads on Cancel only when a lifecycle is embedded (Manage VRAM ON or legacy lifecycle). API prompts without the workflow blob keep that default. Options nodes stay; their token widgets also allow 0 (2026-09-28).

- [x] **A-25 / D-2 implementation - unified Connection Manage VRAM** - one `manage_model_memory` toggle (default ON). Textgen ON/OFF is load-before / unload-after vs no pack load/unload. LM Studio ON keeps TTL + `context_length`; OFF embeds no lifecycle. llama.cpp toggle hidden with status (no verified router load/unload). Model pick still does not call ensure-loaded (Q6). Legacy nodes not removed (2026-09-28).

- [x] **Vir Q6 implementation - no model-pick preload** - removed `ensure_load_on_select` widget; Connection + `model_dropdown.js` no longer call ensure-loaded on model COMBO change; route kept for generate/VRAM (2026-09-28).

- [x] **Vir Q1 - legacy provider disposition** - settled 2026-09-28: retain legacy providers only for compatibility/testing and existing workflows until the Connection path is confirmed; then unregister/hide them. No second maintained product. **Docs only; no unrelated overhaul code.**

- [x] **Vir Q2 - Lifecycle / VRAM direction** - settled 2026-09-28: Connection owns VRAM for new graphs through one user-facing **Manage VRAM / Manage memory** toggle; backend detected or pinned; Textgen and LM Studio keep their existing API paths behind that metaphor. llama.cpp VRAM management is setup-gated on router `/models/load` + `/models/unload`; otherwise chat still works and the toggle is hidden/inert with status. **Toggle shipped as A-25 / D-2** (llama.cpp router path not wired). Separate Lifecycle nodes stay legacy/compatibility only.

- [x] **Vir Q3-Q7 - Options, generate, interrupt, preload, and Auth UX direction** - settled 2026-09-28: probably no separate Options node; at most expose average-user knobs (likely `max_tokens`, maybe temperature) on Generate; converge Basic/Advanced to one Generate node shaped like current Advanced with `max_tokens` above `seed`; respect Manage VRAM and put interrupt/unload policy in node Properties, not main widgets; no `ensure_load_on_select` or model-pick preload, load only on generate or when Manage VRAM needs it; keys stay off-graph, wrong key fails generation loudly with a clear auth flag, and Refresh Node Definitions/config reload is the happy path after settings updates rather than a full restart. **Docs lock only; do not merge/delete Options or collapse the registered nodes yet.**

- [x] **Vir Q8-Q10 + max_tokens - llama.cpp, OpenAI knobs, docs spine, token semantics** - settled 2026-09-28: Connection/OAI `/v1` enough for llama.cpp; dedicated node dead (**D-4 closed**); OpenAI: prefer `max_completion_tokens` (new) / keep `max_tokens` (legacy), send seed when set, no strip-on-cloud, no native Anthropic; README/examples/CODEBASE onto Connection → one Generate (no Options on intended path); `max_tokens` output-only, generous OK, `0`=omit/host default (≥1 send), UI min 1 gap, no artificial prompt caps, user owns OOM/timeout. **Docs lock only.** Q11 not locked — see R-1 research.

- [x] **Systems map / composition** - documented in [`docs/research/2026-09-27-pack-systems-map.md`](docs/research/2026-09-27-pack-systems-map.md) (sockets, overlap, dual paths, debt, keep/demote/kill *hypotheses*, Vir Qs; Q1—Q10 + max_tokens answered; Q11 research note 2026-09-28). Folded comfydesk `notes/2026-09-27-bikeshed-systems-map.md` deltas. Owns `model` vs `loaded_model` smell (research before any sync rule). **Docs only; no code.** Ask Vir before any overhaul.
- [x] **Docs lead on LLM Connection** - README / CHANGELOG / CODEBASE + `example_workflows/connection_basic.json` (`2be26be`, 2026-09-25). Remaining comfydesk UI/UX items (Options height, max_tokens, V3 spike) held pending systems direction / Vir.

