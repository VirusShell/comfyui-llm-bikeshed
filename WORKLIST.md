# Worklist - comfyui-llm-bikeshed

**Updated:** 2026-09-28 (Vir Q1-Q7 settled: legacy providers remain only until Connection is confirmed, then unregister/hide; Connection owns new-graph VRAM through one setup-aware toggle; no separate Options node in the intended spine; one Advanced-shaped Generate node; interrupt policy in node Properties; no model-pick preload; auth stays off-graph with loud auth failure and Refresh Node Definitions/config reload after settings updates; implementation still ask-first; Options merge/delete and height work remain deferred) - Ordered by what is reversible and documented. Older backlog docs (`docs/qol-backlog.md`, `docs/resolution_tracker.md`, proposals, CODEBASE open-design notes) remain **sources for candidates**, not the live queue. This file is the actionable queue.

Legend: `[ ]` todo / `[x]` done / `[~]` deferred (intentionally out of scope now)

---

## Ask-first (do not start without Vir)

- [ ] **A-25 / D-2 implementation follow-up** - unified Connection VRAM toggle and backend-specific command wiring; product direction is settled, but code remains ask-first (`docs/qol-backlog.md`, `docs/resolution_tracker.md`)
- [ ] **DOC-1** off-repo ComfyUI reference corpus disposition: vendor / drop / hybrid
- [ ] **DOC-2** locate or rewrite missing `comfyui-node-standards.md`

## Deferred (only after systems direction)

- [~] **LLM Options node / height** (Textgen 24 toggles / LM Studio 18) - Vir Q3 docs direction is probably no separate Options node; at most expose average-user knobs on Generate and leave the rest to host defaults. Keep current nodes for compatibility, but do not implement merge/delete or height polish until explicitly tasked.
- [~] Empirical lifecycle chain QA (A-15 / A-18 / A-19 / A-22); P-11 URL->model refresh; Cancel cleanup gap — same gate: after composition direction, or ask Vir
- [~] Inline preset dropdown on generation nodes (post-v1; A-6 / qol)
- [~] Dedicated llama.cpp / llama-server node (D-4 tabled); OAI Compatible `/v1` path stays first-class
- [~] Chat nodes, Image Describe, Structured Output, extra cloud APIs (tracker tabled; CODEBASE open-design pointer only)
- [~] Cooperative interrupt for long llama.cpp reasoning without unloading the model (qol Future / research)

## Done (recent)

- [x] **Vir Q1 - legacy provider disposition** - settled 2026-09-28: retain legacy providers only for compatibility/testing and existing workflows until the Connection path is confirmed; then unregister/hide them. No second maintained product. **Docs only; no unrelated overhaul code.**

- [x] **Vir Q2 - Lifecycle / VRAM direction** - settled 2026-09-28: Connection owns VRAM for new graphs through one user-facing **Manage VRAM / Manage memory** toggle; backend detected or pinned; Textgen and LM Studio keep their existing API paths behind that metaphor. llama.cpp VRAM management is setup-gated on router `/models/load` + `/models/unload`; otherwise chat still works and the toggle is hidden/inert with status. **Docs only; unified-toggle implementation is not greenlit.** Separate Lifecycle nodes are legacy/compatibility only for new-graph purposes.

- [x] **Vir Q3-Q7 - Options, generate, interrupt, preload, and Auth UX direction** - settled 2026-09-28: probably no separate Options node; at most expose average-user knobs (likely `max_tokens`, maybe temperature) on Generate; converge Basic/Advanced to one Generate node shaped like current Advanced with `max_tokens` above `seed`; respect Manage VRAM and put interrupt/unload policy in node Properties, not main widgets; no `ensure_load_on_select` or model-pick preload, load only on generate or when Manage VRAM needs it; keys stay off-graph, wrong key fails generation loudly with a clear auth flag, and Refresh Node Definitions/config reload is the happy path after settings updates rather than a full restart. **Docs lock only; do not merge/delete Options or collapse the registered nodes yet.**

- [x] **Systems map / composition** - documented in [`docs/research/2026-09-27-pack-systems-map.md`](docs/research/2026-09-27-pack-systems-map.md) (sockets, overlap, dual paths, debt, keep/demote/kill *hypotheses*, open questions for Vir; Q2 Lifecycle / VRAM and Q3-Q7 direction now answered). Folded richer deltas from comfydesk `notes/2026-09-27-bikeshed-systems-map.md` (VRAM knob conflict, code-voice lag, Options A-1/A-13 evidence, examples gaps, extra Vir Qs). 2026-09-28: also owns `model` vs `loaded_model` selector/status smell (Vir dig; not greenlit alone; overhaul must kill it or schedule local follow). **Docs only; no code.** Ask Vir before any overhaul. Sources: CODEBASE node map + data-flow, Connection lead (`2be26be`), tracker / qol candidates, comfydesk 2026-09-27 systems map, 2026-09-28 dig.
- [x] **Docs lead on LLM Connection** - README / CHANGELOG / CODEBASE + `example_workflows/connection_basic.json` (`2be26be`, 2026-09-25). Remaining comfydesk UI/UX items (Options height, max_tokens, V3 spike) held pending systems direction / Vir.


