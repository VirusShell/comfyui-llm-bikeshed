# Tier 1 provenance audit — operational handoff

**Created:** 2026-06-07  
**Branch:** `research/audit-and-cancel-tracking`  
**Context:** Assessment `f0aad497` found a gap — fresh agents need a single kickoff doc, not chat history.

---

## Start here (read order)

1. **This document** — workflow, checklist, first tasks
2. [`provenance-and-reverification.md`](provenance-and-reverification.md) — citation rules, tier framework, what *not* to assume
3. [`cancel-interrupt-status.md`](cancel-interrupt-status.md) — shipped vs gaps for ComfyUI Cancel during generation
4. [`textgen-lifecycle-verified.md`](textgen-lifecycle-verified.md) — upstream-verified Textgen routes, auth, load/unload

---

## Mission

**Tier 1 provenance re-verification of runtime behavior** — adapters, lifecycle nodes, cancel/interrupt paths. Confirm or correct what the code actually does against primary sources and empirical runs.

| In scope | Out of scope (see below) |
|----------|--------------------------|
| Re-verify claims in Tier 1 files | Re-running the full April 2026 static review |
| Update research docs in place | Declaring all code or tracker rows wrong |
| Flag tracker rows that lack evidence | Tier 2/3 backlog unless touching those files |

**Separate concern:** [`docs/thorough-audit-2026-04-27.md`](../thorough-audit-2026-04-27.md) is a **static code/doc review** from April 2026. Useful background; **not** this operational Tier 1 runtime audit.

---

## Git / workflow

| Item | Value |
|------|--------|
| **Branch** | `research/audit-and-cancel-tracking` |
| **Remote** | Gitea — `http://192.168.1.163:3003/am_Vir/comfyui-llm-bikeshed.git` (**not GitHub**; do not use `gh`) |
| **Base branch** | `master` |
| **Epic context** | `provider-redesign` merged to `master` via Gitea PRs **#5** and **#6** |
| **Docs PR** | Open in Gitea UI when ready — research branch is pushed, **not merged** |
| **Commits** | Prefer **docs-only** commits separate from **code fixes** |

---

## Tier 1 checklist

Work top-down; update **Status** as you verify. All items start **Pending**.

| Area | Files / cross-check | Status |
|------|---------------------|--------|
| Interrupt polling + HTTP abort | `adapters/interrupt.py` | Pending |
| Safe request routing | `adapters/base.py` | Pending |
| Generation + lifecycle HTTP | `adapters/oai_compat.py` | Pending |
| Lifecycle nodes | `nodes/lifecycle.py` | Pending |
| Textgen routes / auth / load-unload | Cross-check [`textgen-lifecycle-verified.md`](textgen-lifecycle-verified.md) | Pending |
| Cancel host-stop (Textgen `stop-generation`) | See [`cancel-interrupt-status.md`](cancel-interrupt-status.md) | Pending |

---

## First 3 tasks (ordered)

1. **Wire + verify Textgen stop-generation on interrupt** — host-side inference stop when ComfyUI Cancel fires; update `cancel-interrupt-status.md` when done.
2. **Re-verify LM Studio TTL / load / unload claims in `oai_compat.py`** — against upstream docs or source at pinned commit; fix code or research note if drift.
3. **Scan `resolution_tracker.md` Decided / Assumed rows for Tier 1 scope** — flag `[VERIFY]` where evidence is docs-only or undated; do **not** promote to Confirmed without empirical or upstream proof.

---

## Outputs

| Deliverable | Where |
|-------------|--------|
| Verified / corrected claims | Update existing `docs/research/*.md` **in place** (no duplicate truths) |
| Runtime surprises | New entry in [`docs/lessons-learned.md`](../lessons-learned.md) per `CLAUDE.md` |
| Cancel progress | [`cancel-interrupt-status.md`](cancel-interrupt-status.md) — shipped vs gaps |
| Tracker honesty | [`resolution_tracker.md`](../resolution_tracker.md) — flag or promote with evidence only |

---

## Out of scope

- **Tier 2 / Tier 3** — parameter allowlists, fingerprinting, proposals (unless a Tier 1 change forces it)
- **Textgen-rehaul lifecycle manager** — separate epic / design work
- **Full April audit re-run** — see [`thorough-audit-2026-04-27.md`](../thorough-audit-2026-04-27.md) as reference only

---

## Quick links

| Doc | Role |
|-----|------|
| [provenance-and-reverification.md](provenance-and-reverification.md) | Provenance standard + tier definitions |
| [cancel-interrupt-status.md](cancel-interrupt-status.md) | Cancel/interrupt shipped vs gaps |
| [textgen-lifecycle-verified.md](textgen-lifecycle-verified.md) | Textgen upstream evidence model |
| [resolution_tracker.md](../resolution_tracker.md) | Project decisions (status ≠ proof) |
| [thorough-audit-2026-04-27.md](../thorough-audit-2026-04-27.md) | April static review (separate) |
