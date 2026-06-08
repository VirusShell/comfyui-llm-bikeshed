# Project-wide provenance audit — operational handoff

**Created:** 2026-06-07  
**Last updated:** 2026-06-08 (reframed — provenance-first)  
**Branch:** `research/audit-and-cancel-tracking`  
**Context:** Assessment `f0aad497` found a gap — fresh agents need a single kickoff doc, not chat history.  
**Fresh chat:** paste full contents of [`fresh-context-audit-prompt.md`](fresh-context-audit-prompt.md).

---

## Mission (read this first)

**Determine whether the project was built on bad or unverified information** — across docs, `resolution_tracker.md`, research notes, reference docs, proposals, and code assumptions — and fix the provenance trail before treating any area as "done."

| Primary (Tier 1) | Secondary (Tier 2+) | Not the headline |
|------------------|---------------------|------------------|
| Claim inventory & citation freshness | Runtime code paths vs upstream | Empirical Textgen/LM Studio cancel QA |
| Tracker `Decided`/`Assumed`/`Contaminated` audit | Adapter/lifecycle wiring verification | Mock cancel tests |
| Reference docs vs code alignment | Parameter allowlists, fingerprinting | Interrupt cleanup product decision |
| Concept/scope docs vs shipped code | | |

**Separate concerns:**

- [`docs/thorough-audit-2026-04-27.md`](../thorough-audit-2026-04-27.md) — April 2026 **static** code/doc review; background only.
- [`cancel-interrupt-status.md`](cancel-interrupt-status.md) — Cancel **shipped vs gaps**; update when interrupt behavior changes.
- [`cancel-empirical-qa-handoff.md`](cancel-empirical-qa-handoff.md) — optional live cancel QA for humans with GPU + backends (protocol **not** in this doc).

---

## Why agents drifted to cancel QA

Prior versions of this handoff and [`fresh-context-audit-prompt.md`](fresh-context-audit-prompt.md) caused repeated mis-framing. Specific triggers:

| Drift source | Problem |
|--------------|---------|
| Doc title "Tier 1 provenance audit" + mission "runtime behavior — cancel/interrupt paths" | Equated Tier 1 with adapter/cancel code, not project-wide provenance |
| Tier 1 checklist = only `adapters/*`, lifecycle, cancel rows | No tracker sweep, no `docs/research/*.md` inventory, no reference-doc alignment |
| § **Next work** priorities 1–2 = live Textgen/LM Studio cancel QA | Agents treated GPU QA as the mandatory next session |
| `fresh-context-audit-prompt.md` **Start by:** "single next Tier 1 `[VERIFY]` task" | `[VERIFY]` flags were on cancel/lifecycle rows only → cancel QA every time |
| `provenance-and-reverification.md` Tier 1 = "Runtime behavior" | Tier numbers reinforced cancel-first ordering |
| Branch name `research/audit-and-cancel-tracking` | Name suggests cancel is the audit subject |
| Read order: `cancel-interrupt-status.md` before tracker | Cancel doc elevated above contamination audit |

**Correction:** Tier 1 is now the **project-wide provenance sweep**. Cancel empirical QA lives in [`cancel-empirical-qa-handoff.md`](cancel-empirical-qa-handoff.md) (optional). Tier 2 holds runtime code-path checks completed 2026-06-07/08.

---

## Start here (read order)

1. **This document** — mission, Tier 1 checklist, next work
2. [`provenance-and-reverification.md`](provenance-and-reverification.md) — citation rules, tier framework
3. [`resolution_tracker.md`](../resolution_tracker.md) — decisions to audit (status ≠ proof)
4. [`cancel-interrupt-status.md`](cancel-interrupt-status.md) — **only** when working cancel/interrupt shipped-vs-gaps (not empirical QA protocol)

---

## Git / workflow

| Item | Value |
|------|--------|
| **Branch** | `research/audit-and-cancel-tracking` |
| **Remote** | Gitea — `http://192.168.1.163:3003/am_Vir/comfyui-llm-bikeshed.git` (**not GitHub**; do not use `gh`) |
| **Base branch** | `master` |
| **Epic context** | `provider-redesign` merged to `master` via Gitea PRs **#5** and **#6** |
| **Docs PR** | Open in Gitea UI when ready — research branch is pushed, **not merged** |

---

## Tier 1 — Project-wide provenance sweep (PRIMARY)

Work top-down. Update **Status** as you verify. Goal: every external claim has traceable provenance or an honest `[VERIFY]` / `Contaminated` flag.

| # | Area | What to do | Key paths | Status |
|---|------|------------|-----------|--------|
| 1.1 | **Resolution tracker contamination audit** | For each `Decided`, `Assumed`, `Confirmed`, and any `Contaminated` row: list external citations in Notes; check source date + status; downgrade or flag if evidence is docs-only, undated, or stale | `docs/resolution_tracker.md` | **Pending** — ad hoc `[VERIFY]` on A-15, A-18, A-19, A-22 only |
| 1.2 | **Research claim inventory** | Build/update provenance tables in each `docs/research/*.md`: URL, source date, access date, verified how, applies-to | `docs/research/*.md` | **Partial** — `textgen-lifecycle-verified.md`, `lm-studio-lifecycle-verified.md` are templates; others need pass |
| 1.3 | **Reference docs vs code** | Diff allowlists, routes, auth, platform patterns against adapters and nodes | `docs/reference/backend-api-parameters.md`, `implementation-patterns.md`, `comfyui-platform-findings.md` vs `adapters/`, `nodes/` | **Pending** — `backend-api-parameters.md` last updated 2026-03-09 |
| 1.4 | **Concept & scope vs code** | Reconcile `text_gen_processing_concept.md`, `CLAUDE.md`, S-2/v1 scope with shipped nodes and adapters | `docs/text_gen_processing_concept.md`, `CLAUDE.md`, `docs/proposals/product-direction-and-scope.md` | **Pending** |
| 1.5 | **External citation freshness** | Per `provenance-and-reverification.md`: re-fetch issues/PRs cited in tracker, lessons-learned, reference docs; record open/closed/superseded | Cross-cutting | **Pending** |
| 1.6 | **Off-repo corpus disposition** | DOC-1/DOC-2 — inventory complete; owner decision still open | `external-comfyui-reference-corpus.md`, tracker DOC-1, DOC-2 | **Unresolved** (owner) |
| 1.7 | **Lessons-learned URL audit** | External URLs inside `docs/lessons-learned.md` — incident narrative may be trusted; citations need separate freshness check | `docs/lessons-learned.md` | **Pending** |
| 1.8 | **Proposals vs reality** | Flag proposal assumptions contradicted by code or upstream changes | `docs/proposals/*.md`, D-1–D-4 rows | **Pending** |

**Tier 1 done when:** Each row above is **Verified** (sweep complete, gaps documented) or explicitly **Deferred** with owner reason — not when cancel QA finishes.

---

## Tier 2 — Runtime code-path verification (SECONDARY)

Confirm shipped code matches primary sources. Completed as a **narrow slice** 2026-06-07/08; re-verify when Tier 1 flags a stale citation in these paths.

| Area | Files / cross-check | Status |
|------|---------------------|--------|
| Interrupt polling + HTTP abort | `adapters/interrupt.py` | **Verified** — code read 2026-06-07, re-read 2026-06-08 |
| Safe request routing | `adapters/base.py` | **Verified** — re-read 2026-06-08 |
| Generation + lifecycle HTTP | `adapters/oai_compat.py` | **Verified** — Textgen `on_interrupt` → `stop-generation`; LM Studio REST parse + instance_id unload |
| Lifecycle nodes | `nodes/lifecycle.py` | **Verified** — re-read 2026-06-08 |
| Textgen routes / auth / load-unload | [`textgen-lifecycle-verified.md`](textgen-lifecycle-verified.md) | **Verified** — pack code re-read 2026-06-08 |
| LM Studio TTL / load / unload | [`lm-studio-lifecycle-verified.md`](lm-studio-lifecycle-verified.md) | **Verified** (docs + code read); live behavior **[VERIFY]** via [`cancel-empirical-qa-handoff.md`](cancel-empirical-qa-handoff.md) |
| Cancel host-stop wiring | [`cancel-interrupt-status.md`](cancel-interrupt-status.md) | **Partial** — wired in code; empirical stop behavior **[VERIFY]** via [`cancel-empirical-qa-handoff.md`](cancel-empirical-qa-handoff.md) |

---

## Tier 3 — Design backlog provenance

Lower urgency unless shipping that work. See `provenance-and-reverification.md` §5.

| Area | Examples | Status |
|------|----------|--------|
| Proposals | `docs/proposals/*`, D-1, D-2 | **Pending** |
| QoL / open platform rows | P-2 ecosystem patterns, AA-6 cross-version COMBO | **Pending** |
| Tabled features | A-5, A-12, cloud APIs | **Deferred** (out of v1) |

---

## Next work (ordered) — provenance first

| Priority | Task | Tier | Notes |
|----------|------|------|-------|
| **1** | **Resolution tracker contamination audit** — spreadsheet or table: row ID, status, external cites in Notes, evidence grade, action | 1.1 | Start here every fresh session until complete |
| **2** | **Research `*.md` claim inventory** — add/fix provenance tables; mark stale claims | 1.2 | Use `textgen-lifecycle-verified.md` as template |
| **3** | **`backend-api-parameters.md` vs code** — allowlists, dropped params, backend-specific names | 1.3 | Last doc update 2026-03-09 |
| **4** | **`comfyui-platform-findings.md` + `implementation-patterns.md` vs code** — P-9, P-10, node patterns | 1.3 | P-10 underpins A-15 |
| **5** | **Concept / CLAUDE / S-2 vs shipped nodes** — list mismatches | 1.4 | CLAUDE still says "pre-implementation" |
| **6** | **Re-fetch cited issues/PRs** — especially LM Studio #1463 (A-22), any closed 2023 threads | 1.5 | Record status + date in research notes |
| **7** | **Lessons-learned external URL pass** | 1.7 | Trust narrative; verify URLs |
| **8** | Tier 2 re-read | 2 | Only if Tier 1 flags drift in a file |

**Do not put empirical cancel QA in this table.** Protocol and open items: [`cancel-empirical-qa-handoff.md`](cancel-empirical-qa-handoff.md).

---

## Completed slice (2026-06-07) — Tier 2 wiring

These were the **first runtime fixes** that motivated the audit branch; they do **not** close Tier 1:

1. Textgen `stop-generation` wired on interrupt — code read + `oai_compat.py` / `interrupt.py`
2. LM Studio REST `models[].key` parse + `instance_id` unload — `lm-studio-lifecycle-verified.md`
3. Surgical `[VERIFY]` on A-15, A-18, A-19, A-22, API-6 note corrected

---

## Session log

| Date | Focus | Outcome |
|------|-------|---------|
| 2026-06-07 | Tier 2 runtime fixes + research notes | Textgen stop-generation wired; LM Studio REST parse fixed; handoff docs created |
| 2026-06-08 | Fresh-context resume (mis-framed) | Code re-read; empirical QA protocol added; agents directed to cancel QA as "next" — **corrected 2026-06-08** by reframing Tier 1 as project-wide provenance |
| 2026-06-08 | Handoff reframe | Tier 1 = provenance sweep; cancel QA demoted to [`cancel-empirical-qa-handoff.md`](cancel-empirical-qa-handoff.md); next-work table provenance-first |

---

## Outputs

| Deliverable | Where |
|-------------|--------|
| Claim inventory & provenance tables | `docs/research/*.md` **in place** |
| Tracker honesty | `resolution_tracker.md` — flag `Contaminated` or promote with evidence |
| Reference alignment | Update `docs/reference/*.md` when code diverges |
| Runtime surprises | `docs/lessons-learned.md` |
| Cancel shipped vs gaps (subsidiary) | `cancel-interrupt-status.md` |
| Cancel empirical QA runs (subsidiary) | `cancel-empirical-qa-handoff.md` |

---

## Out of scope

- **Textgen-rehaul lifecycle manager** — separate epic
- **Full April audit re-run** — `thorough-audit-2026-04-27.md`
- **Declaring all research invalid** without per-claim audit
- **Skipping Tier 1** to run live cancel QA

---

## Quick links

| Doc | Role |
|-----|------|
| [provenance-and-reverification.md](provenance-and-reverification.md) | Provenance standard + tier definitions |
| [fresh-context-audit-prompt.md](fresh-context-audit-prompt.md) | Paste into new agent chat |
| [cancel-interrupt-status.md](cancel-interrupt-status.md) | Cancel shipped vs gaps (code-read status) |
| [cancel-empirical-qa-handoff.md](cancel-empirical-qa-handoff.md) | Live cancel QA protocol (subsidiary; human-run) |
| [textgen-lifecycle-verified.md](textgen-lifecycle-verified.md) | Textgen upstream evidence model |
| [lm-studio-lifecycle-verified.md](lm-studio-lifecycle-verified.md) | LM Studio evidence model |
| [resolution_tracker.md](../resolution_tracker.md) | Project decisions (status ≠ proof) |
