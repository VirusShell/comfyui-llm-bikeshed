# Worklist - comfyui-llm-bikeshed

**Updated:** 2026-09-28 (Vir Q1 settled: legacy providers remain only until Connection is confirmed, then unregister/hide; Options polish still deferred) - Ordered by what is reversible and documented. Older backlog docs (`docs/qol-backlog.md`, `docs/resolution_tracker.md`, proposals, CODEBASE open-design notes) remain **sources for candidates**, not the live queue. This file is the actionable queue.

Legend: `[ ]` todo / `[x]` done / `[~]` deferred (intentionally out of scope now)

---

## Ask-first (do not start without Vir)

- [ ] **A-25 / D-2** provider vs lifecycle consolidation / lifecycle UX rethink (`docs/qol-backlog.md`, `docs/resolution_tracker.md`)
- [ ] **DOC-1** off-repo ComfyUI reference corpus disposition: vendor / drop / hybrid
- [ ] **DOC-2** locate or rewrite missing `comfyui-node-standards.md`

## Deferred (only after systems direction)

- [~] **LLM Options node height** (Textgen 24 toggles / LM Studio 18) — polish held until systems map says Options stay as-is; ask Vir before implementing (`docs/qol-backlog.md`)
- [~] Empirical lifecycle chain QA (A-15 / A-18 / A-19 / A-22); P-11 URL->model refresh; Cancel cleanup gap — same gate: after composition direction, or ask Vir
- [~] Inline preset dropdown on generation nodes (post-v1; A-6 / qol)
- [~] Dedicated llama.cpp / llama-server node (D-4 tabled); OAI Compatible `/v1` path stays first-class
- [~] Chat nodes, Image Describe, Structured Output, extra cloud APIs (tracker tabled; CODEBASE open-design pointer only)
- [~] Cooperative interrupt for long llama.cpp reasoning without unloading the model (qol Future / research)

## Done (recent)

- [x] **Vir Q1 - legacy provider disposition** - settled 2026-09-28: retain legacy providers only for compatibility/testing and existing workflows until the Connection path is confirmed; then unregister/hide them. No second maintained product. **Docs only; no unrelated overhaul code.**

- [x] **Systems map / composition** - documented in [`docs/research/2026-09-27-pack-systems-map.md`](docs/research/2026-09-27-pack-systems-map.md) (sockets, overlap, dual paths, debt, keep/demote/kill *hypotheses*, open questions for Vir). Folded richer deltas from comfydesk `notes/2026-09-27-bikeshed-systems-map.md` (VRAM knob conflict, code-voice lag, Options A-1/A-13 evidence, examples gaps, extra Vir Qs). 2026-09-28: also owns `model` vs `loaded_model` selector/status smell (Vir dig; not greenlit alone; overhaul must kill it or schedule local follow). **Docs only; no code.** Ask Vir before any overhaul. Sources: CODEBASE node map + data-flow, Connection lead (`2be26be`), tracker / qol candidates, comfydesk 2026-09-27 systems map, 2026-09-28 dig.
- [x] **Docs lead on LLM Connection** - README / CHANGELOG / CODEBASE + `example_workflows/connection_basic.json` (`2be26be`, 2026-09-25). Remaining comfydesk UI/UX items (Options height, max_tokens, V3 spike) held pending systems direction / Vir.


