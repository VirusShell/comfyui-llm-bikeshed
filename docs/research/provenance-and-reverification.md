# Research Provenance and Re-verification

**Created:** 2026-06-07  
**Status:** Authoritative project-wide guidance — read before trusting or extending research-derived decisions.

---

## 1. Purpose

This document exists because **research provenance failures are project-wide**, not isolated to one feature area.

During June 2026 work on cooperative cancel / interrupt handling, an agent cited a **closed 2023 GitHub issue** as current ComfyUI behavior **without recording access date, issue status, or whether upstream had changed since**. That pattern can invalidate any decision built on external claims — adapter logic, lifecycle design, parameter allowlists, tracker rows, and proposals alike.

**What this doc is:** a single place to understand known vs unknown provenance, how to cite sources going forward, and how to resume work without a full audit.

**What this doc is not:** a claim that the codebase or all decisions are wrong, or a complete re-verification checklist.

### Operational kickoff (Tier 1 audit)

For **hands-on Tier 1 re-verification** (branch, checklist, first tasks, Gitea workflow), start with [`audit-handoff.md`](audit-handoff.md). This document remains the **provenance rules** reference; the handoff doc is the **execution** entry point.

---

## 2. Scope of the problem

| This is **not** saying | This **is** saying |
|------------------------|-------------------|
| All code is broken | Claims from **external research without dated provenance** cannot be treated as verified until re-checked |
| Every `Decided` row in the tracker is invalid | Tracker status reflects **project intent at write time**, not automatic proof against live upstream |
| Cancel/interrupt is the only risky area | Cancel research **surfaced** a general pattern; the same risk applies wherever research was copied without audit trail |
| Ollama removal or other shipped decisions are void | Those decisions stand on their **own** evidence until a targeted audit says otherwise — do not invalidate without review |

### Categories affected (non-exhaustive)

| Category | Examples in this repo |
|----------|----------------------|
| **Adapter runtime behavior** | `adapters/oai_compat.py`, `adapters/interrupt.py`, HTTP paths, auth headers, error handling |
| **Lifecycle / VRAM** | LM Studio TTL, Textgen load/unload, chain deferral (A-15), lifecycle nodes |
| **API parameters** | `docs/reference/backend-api-parameters.md`, Options node allowlists |
| **Resolution tracker rows** | `docs/resolution_tracker.md` — especially `Decided` / `Assumed` backed by old research |
| **Proposals & backlog** | `docs/proposals/*.md`, `docs/qol-backlog.md` |
| **Lessons learned** | `docs/lessons-learned.md` — accurate for incidents described, but external citations inside entries may age |
| **Verified research notes** | `docs/research/textgen-lifecycle-verified.md` — model for good provenance; still version-sensitive |
| **ComfyUI platform assumptions** | Queue model, cancel semantics, widget behavior — often sourced from issues/discussions |

**Known good counterexample:** `textgen-lifecycle-verified.md` cites upstream file URLs, access date, and separates confirmed vs unknown — use it as the template for new research notes.

---

## 3. What triggered this (illustration only)

**Context:** Investigating whether ComfyUI Cancel stops in-flight LLM HTTP calls.

**Failure mode:** A GitHub issue ([oobabooga/textgen #4521](https://github.com/oobabooga/textgen/issues/4521), closed 2023-11-09) was cited as evidence for Textgen cancel behavior without access date, closed/open status, or checking whether the claim applied to this pack’s non-streaming requests. No distinction between “maintainer workaround in a closed thread” and “verified current behavior.”

**Actual outcome (partially verified separately):** ComfyUI sets an interrupt flag; custom nodes must poll cooperatively — see `docs/lessons-learned.md` (2026-06-03 entry) and `adapters/interrupt.py`. That fix is **one verified slice**; it does not prove all other research in the repo is current.

Use this episode as a **pattern warning**, not as the full scope of re-verification work.

---

## 4. Provenance standard (going forward)

Every external claim that influences code or a `Decided` tracker row should be traceable in a research note or PR description using this minimum set:

| Field | Required content |
|-------|------------------|
| **Source URL** | Canonical link (prefer upstream repo file/commit or official docs, not wiki mirrors) |
| **Access date** | ISO date when the source was read (e.g. `2026-06-07`) |
| **Issue / PR status** | If applicable: open, closed, merged, superseded — and **which** if multiple related threads exist |
| **Upstream version / commit** | Tag, release, or commit SHA when citing code; branch name if floating |
| **Verified how** | One of: `code read`, `empirical` (live backend/ComfyUI run), `docs only` (mark weaker) |
| **Applies to** | File path, tracker ID, or feature name this evidence supports |

### Research note template (copy for new files under `docs/research/`)

```markdown
# [Topic] — verified / partial / stale

**Date:** YYYY-MM-DD
**Scope:** [what this note covers]

## Sources
| Topic | URL | Access date | Status / commit | Verified how |
|-------|-----|-------------|-----------------|--------------|

## Confirmed behavior
- …

## Unknown / version-sensitive
- …

## Applies to
- [files, tracker rows, nodes]
```

**Rule:** `docs only` without code read or empirical check is acceptable for **exploration**; it is **not** sufficient alone to mark a tracker row `Confirmed` or ship behavior-critical logic.

---

## 5. Re-verification priority tiers

Framework only — not a full audit list. Work top-down when time allows; do not block all shipping on completing Tier 3.

| Tier | Focus | Why first | Examples |
|------|--------|-----------|----------|
| **1 — Runtime behavior** | Adapters, lifecycle, cancel/interrupt, load/unload | Direct user impact; wrong behavior wastes VRAM or hangs queues | `adapters/*`, lifecycle nodes, interrupt polling |
| **2 — API & detection** | Parameter allowlists, model list paths, backend fingerprinting | Silent wrong params or empty dropdowns | `backend-api-parameters.md`, `model_list.py`, provider detection |
| **3 — Design backlog** | Proposals, QoL items, non-shipped architecture | Lower immediate risk if not implemented | `docs/proposals/*`, open tracker `Unresolved` rows |

When touching Tier 1 code, re-verify **that path** even if the wider audit is incomplete.

---

## 6. For agents / new context

1. **Read this document first** when resuming research-heavy work or citing GitHub/issues/docs.
2. **Do not treat `Decided` in `resolution_tracker.md` as verified fact** — check provenance or re-verify before extending behavior.
3. **Mark uncertain work `[VERIFY]`** in specs/tasks when evidence is docs-only or undated.
4. **Before changing Textgen paths or auth**, read and update `docs/research/textgen-lifecycle-verified.md` if upstream changed.
5. **Prefer primary sources:** upstream `script.py` / API routes over blog posts; ComfyUI source or reproducible run over old issues.
6. **Update provenance when you verify:** add access date and commit; move claims from “assumed” to “confirmed” in the research note, not only in chat.
7. **Do not expand scope** by declaring unrelated decisions invalid — audit the area you touch.

---

## 7. For humans — resuming work

**Start here:**

1. This document (provenance rules and tiers)
2. `docs/resolution_tracker.md` (what the project decided — with status key)
3. `docs/research/*.md` and `docs/reference/*.md` for backend-specific notes

**Practical workflow:**

- Audit **tier-by-tier** when planning a release or large refactor; skip Tier 3 if not shipping that work.
- **Do not block** urgent fixes on a full-repo audit — but **do** re-verify sources for the files you change.
- **Do not add features** on stale wiki/issue citations without a fresh research note row in the table above.
- When a lesson-learned entry fixes real runtime behavior, trust the **incident narrative**; re-check any **external URLs** inside it separately.

---

## 8. Related docs to update over time

Keep provenance fresh in these locations when re-verifying (edit in place; do not duplicate conflicting truths):

| Document | Update when |
|----------|-------------|
| `docs/research/textgen-lifecycle-verified.md` | Textgen routes, auth, or load/unload behavior changes |
| `docs/research/lm-studio-lifecycle-verified.md` | LM Studio TTL, load/unload, or REST list API changes |
| `docs/reference/backend-api-parameters.md` | Parameter allowlists or backend differences change |
| `docs/resolution_tracker.md` | Promoting Assumed → Confirmed, or flagging Contaminated |
| `docs/lessons-learned.md` | Non-obvious runtime fixes (mandatory per `CLAUDE.md`) |
| `docs/research/provenance-and-reverification.md` | Process changes or new tier guidance |
| `docs/research/cancel-interrupt-status.md` | Cancel/interrupt shipped vs gaps |
| `CLAUDE.md` | Pointers to authoritative research paths |
| Feature-specific proposals under `docs/proposals/` | When implementation proves or disproves design assumptions |

---

## 9. Do not

- Use alarmist language (“everything is broken,” “all research is trash”).
- Imply cancel/interrupt is the **only** area needing provenance discipline.
- Invalidate decisions (e.g. Ollama removal, provider split) **without** a targeted audit of that decision’s evidence.
- Copy GitHub issue numbers into code comments without date and status.
- Mark tracker rows `Confirmed` from docs-only reads of third-party summaries.

---

## 10. Related tracking (separate concerns)

Cancel/interrupt work **triggered** provenance review but has its **own** progress doc — do not conflate “cancel not finished” with “all research is invalid.”

| Document | Tracks |
|----------|--------|
| [`cancel-interrupt-status.md`](cancel-interrupt-status.md) | What is **shipped** vs **gaps** for ComfyUI Cancel during generation (all providers) |
| This document | How to **cite and re-verify** research project-wide |

Update `cancel-interrupt-status.md` when interrupt behavior changes; update this doc when process rules change.

---

## Quick reference

**Trust hierarchy (strongest first):** empirical run in target environment → upstream source at pinned commit → official docs → issue/discussion with date + status → wiki/blog/unsourced agent output.

**When in doubt:** add a row to a `docs/research/` note, leave tracker status honest (`Assumed` / `Unresolved`), and verify the slice you are changing.
