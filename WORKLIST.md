# Worklist - comfyui-llm-bikeshed

**Updated:** 2026-09-27 (docs Connection marked done; UX implement held) - Ordered by what is reversible and documented. Older backlog docs (`docs/qol-backlog.md`, `docs/resolution_tracker.md`, proposals, CODEBASE open-design notes) remain **sources for candidates**, not the live queue. This file is the actionable queue.

Legend: `[ ]` todo / `[x]` done / `[~]` deferred (intentionally out of scope now)

---

## Open / polish

- [ ] **Evaluate LLM Options: Textgen node height** in live ComfyUI (24 toggles) - implement as single node first; split only if it looks bad (`docs/qol-backlog.md`)
- [ ] **Evaluate LLM Options: LM Studio node height** in live ComfyUI (18 toggles) - same rule (`docs/qol-backlog.md`)
- [ ] **Empirical lifecycle chain QA** for tracker `[VERIFY]` on A-15 / A-18 / A-19 / A-22 (live Textgen + LM Studio) - `docs/resolution_tracker.md` + lifecycle research notes
- [ ] **Re-verify P-11** URL -> model dropdown refresh with OAI Compatible + Textgen on one graph (`docs/resolution_tracker.md`)
- [ ] **Cancel cleanup gap** - unload / TTL follow-through when Cancel interrupts mid-generate (`docs/research/cancel-interrupt-status.md`); ask Vir before productizing host-stop beyond Textgen

## Ask-first (do not start without Vir)

- [ ] **A-25 / D-2** provider vs lifecycle consolidation / lifecycle UX rethink (`docs/qol-backlog.md`, `docs/resolution_tracker.md`)
- [ ] **DOC-1** off-repo ComfyUI reference corpus disposition: vendor / drop / hybrid
- [ ] **DOC-2** locate or rewrite missing `comfyui-node-standards.md`

## Deferred

- [~] Inline preset dropdown on generation nodes (post-v1; A-6 / qol)
- [~] Dedicated llama.cpp / llama-server node (D-4 tabled); OAI Compatible `/v1` path stays first-class
- [~] Chat nodes, Image Describe, Structured Output, extra cloud APIs (tracker tabled; CODEBASE open-design pointer only)
- [~] Cooperative interrupt for long llama.cpp reasoning without unloading the model (qol Future / research)

## Done (recent)

- [x] **Docs lead on LLM Connection** - README / CHANGELOG / CODEBASE + `example_workflows/connection_basic.json` (`2be26be`, 2026-09-25). Remaining comfydesk UI/UX items (Options height, max_tokens, V3 spike) held pending confirmation research.
