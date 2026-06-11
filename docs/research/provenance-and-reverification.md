# Research Provenance and Decision-Time Prevention

**Created:** 2026-06-07  
**Updated:** 2026-06-08 — reframed for prevention at write/decision time  
**Status:** Authoritative guidance for new research, tracker updates, and behavior changes.

---

## 1. Mission — prevent bad intel at decision time

This pack works. The recurring failure mode is **locking in unverified external claims** as if they were confirmed fact — then building tracker rows, adapters, and docs on top of them.

**Primary mission:** stop that at the moment you write research, mark a tracker row, or ship behavior. **Not** a mandate to re-audit the whole repo before every fix.

**Gold template:** [`textgen-lifecycle-verified.md`](textgen-lifecycle-verified.md) — upstream URLs, access dates, confirmed vs unknown, falsifiers implied by version-sensitive sections. New notes: copy [`research-note-template.md`](research-note-template.md).

**What triggered the discipline (illustration):** During cancel/interrupt work, a **closed 2023 GitHub issue** was cited as current Textgen behavior without access date, issue status, or checking applicability to this pack's non-streaming path. That pattern can appear anywhere — not only cancel. See § 8 for the episode; use it as a write-time warning, not as proof everything else is stale.

---

## 2. Decision-time gates

Apply these **before** the claim becomes durable project truth.

### Gate A — Writing research (`docs/research/*.md`)

| Before you save | Requirement |
|-----------------|-------------|
| External claim influences a conclusion | Source URL (prefer upstream file/commit or official docs) |
| Claim may age | Access date (ISO `YYYY-MM-DD`) |
| GitHub issue/PR cited | Open / closed / merged / superseded — and which thread if several exist |
| Code citation | Branch/tag/commit SHA when possible |
| Strength of evidence | `code read`, `empirical`, or `docs only` (weaker — see below) |
| Downstream use | **Applies to** — files, tracker IDs, features |
| Honesty about limits | **Falsifiers** — what observation would disprove the claim |
| Maintenance | **Re-check triggers** — when to re-open the note (see § 4) |

Use the template: [`research-note-template.md`](research-note-template.md).

### Gate B — Tracker rows (`docs/resolution_tracker.md`)

| Action | Rule |
|--------|------|
| Mark **`Confirmed`** | Verified against **primary source** — `code read`, `empirical`, or pinned upstream — not docs-only third-party summaries |
| Mark **`Decided`** | Human/product choice with rationale; **not** an external fact claim |
| Leave **`Assumed`** | Workable hypothesis; do not pretend it was verified |
| Add **`[VERIFY]`** in Notes | Needs check before driving behavior or promoting status |
| Promote `Assumed` → `Confirmed` | Update or add a research note row; do not promote from chat alone |
| **`Contaminated`** | Foundation assumption failed or unverified — fix evidence before extending |

Status definitions: [`resolution_tracker.md`](../resolution_tracker.md) § Status definitions.

**Do not treat `Decided` or `Assumed` as verified fact** when extending code — check provenance for the slice you touch.

### Gate C — Shipping behavior (adapters, nodes, reference docs)

| Before merge / ship | Rule |
|---------------------|------|
| Behavior depends on upstream API or ComfyUI semantics | Matching research note exists and **Applies to** lists the files you changed |
| Textgen paths, auth, load/unload | Read and update [`textgen-lifecycle-verified.md`](textgen-lifecycle-verified.md) if upstream changed |
| LM Studio lifecycle | Same for [`lm-studio-lifecycle-verified.md`](lm-studio-lifecycle-verified.md) |
| Citation is issue/discussion only | Re-fetch or read primary source; record date + status |
| Uncertain after gate | Ship with honest tracker/research state (`Assumed`, `[VERIFY]`) — not silent `Confirmed` |

**Practical rule:** Re-verify **sources for the path you change**. Do not block urgent fixes on a full-repo sweep.

---

## 3. Write-time citation standard

Every external claim that passes Gate A should be traceable with at least:

| Field | Required content |
|-------|------------------|
| **Source URL** | Canonical link (upstream repo file/commit or official docs; not wiki mirrors) |
| **Access date** | ISO date when read (e.g. `2026-06-08`) |
| **Issue / PR status** | If applicable: open, closed, merged, superseded |
| **Upstream version / commit** | Tag, release, or SHA when citing code |
| **Verified how** | `code read` \| `empirical` \| `docs only` |
| **Applies to** | File path, tracker ID, or feature name |

**`docs only`** is fine for exploration. It is **not** sufficient alone to mark a tracker row `Confirmed` or ship behavior-critical logic.

---

## 4. Falsifiers and re-check triggers

### Falsifiers

For each important claim, record **what would prove it wrong** — concrete and observable:

- Route returns different status or shape than documented
- Upstream removes or renames the cited symbol/path
- Live backend behaves differently from the cited issue thread
- ComfyUI version changes widget/queue semantics you relied on

If you cannot name a falsifier, the claim is still a hypothesis — keep tracker status at `Assumed` or `[VERIFY]`.

### Re-check triggers (staleness)

Re-open the research note and re-run Gate A when:

| Trigger | Examples |
|---------|----------|
| **You touch Applies-to code/docs** | Editing `adapters/oai_compat.py` after a Textgen cite |
| **Upstream movement** | New release, default branch rename, API deprecation |
| **Empirical mismatch** | Test or user report matches a falsifier |
| **Promotion** | Moving tracker row toward `Confirmed` |
| **Time + volatility** | Old issue/discussion cite on fast-moving upstream (>6–12 months without `code read`) |
| **Lessons-learned URLs** | Trust incident narrative; re-check external links inside entries separately |

---

## 5. Trust hierarchy

Strongest first:

1. **Empirical** — reproduced in target environment (ComfyUI + live backend)
2. **Upstream source** — pinned commit / file read on canonical repo
3. **Official docs** — vendor or project documentation
4. **Issue / discussion** — with access date + open/closed status + applicability note
5. **Wiki / blog / unsourced agent output** — exploration only until upgraded

**When in doubt:** add a research note row, leave tracker status honest (`Assumed` / `Unresolved`), verify the slice you are changing.

---

## 6. Scope of the problem (calibrated)

| This is **not** saying | This **is** saying |
|------------------------|-------------------|
| All code is broken | Undated or stale external cites **must not** become silent `Confirmed` facts |
| Every `Decided` row is invalid | `Decided` = product intent; re-check **external** evidence when behavior depends on it |
| Cancel is the only risky area | Cancel **surfaced** a general write-time pattern |
| Shipped decisions are void without audit | Ollama removal and similar stand on **their own** evidence until a targeted check says otherwise |

**Categories where gates matter:** adapters, lifecycle/VRAM, API parameters, tracker rows, proposals, ComfyUI platform assumptions, lessons-learned external URLs.

---

## 7. For agents / new context

**Fresh chat (default):** paste [`fresh-context-prevention-prompt.md`](fresh-context-prevention-prompt.md) for feature/bug work. **Backward inventory:** abandoned — historical checklist in [`docs/the-archive/2026-06-08-provenance-audit-handoff-abandoned.md`](../the-archive/2026-06-08-provenance-audit-handoff-abandoned.md).

1. **Read this document** before citing GitHub/issues/docs or extending research-derived behavior.
2. **Use [`research-note-template.md`](research-note-template.md)** for new `docs/research/` notes.
3. **Check [`resolution_tracker.md`](../resolution_tracker.md)** — status ≠ proof; see § Status definitions.
4. **Mark uncertain work `[VERIFY]`** in tracker Notes or specs when evidence is docs-only or undated.
5. **Prefer primary sources:** upstream `script.py` / API routes over blog posts; ComfyUI source or reproducible run over old issues.
6. **Update provenance when you verify:** access date and commit in the research note, not only in chat.
7. **Do not expand scope** by declaring unrelated decisions invalid — apply gates to the area you touch.

**Backward-looking repo sweep:** **Abandoned** (2026-06-11). See [`audit-handoff.md`](audit-handoff.md) for pointer to the archive. Prevention rules here remain authoritative for **new** work.

---

## 8. Illustration — cancel provenance episode

**Context:** Whether ComfyUI Cancel stops in-flight LLM HTTP calls.

**Failure mode:** GitHub issue ([oobabooga/textgen #4521](https://github.com/oobabooga/textgen/issues/4521), closed 2023-11-09) cited without access date, status, or applicability to non-streaming requests. No line between "maintainer workaround in a closed thread" and "verified current behavior."

**Verified slice (separate):** ComfyUI sets an interrupt flag; custom nodes poll cooperatively — `docs/lessons-learned.md` (2026-06-03), `adapters/interrupt.py`. That does not prove all other research is current.

---

## 9. Backward audit (abandoned)

A **project-wide provenance inventory** was planned in 2026-06 but **abandoned** 2026-06-11. The historical checklist lives in [`docs/the-archive/2026-06-08-provenance-audit-handoff-abandoned.md`](../the-archive/2026-06-08-provenance-audit-handoff-abandoned.md). Decision-time gates in this document are the ongoing standard.

Brief tier reminder (archived handoff only):

| Tier | Focus |
|------|--------|
| **1** | Claim inventory, tracker audit, reference/concept vs code |
| **2** | Runtime paths — adapters, lifecycle, interrupt vs upstream |
| **3** | Proposals, QoL, non-shipped design |

Empirical cancel QA is subsidiary — [`cancel-empirical-qa-handoff.md`](cancel-empirical-qa-handoff.md).

---

## 10. Related docs to keep fresh

Edit in place when re-verifying; do not duplicate conflicting truths.

| Document | Update when |
|----------|-------------|
| `docs/research/textgen-lifecycle-verified.md` | Textgen routes, auth, load/unload change |
| `docs/research/lm-studio-lifecycle-verified.md` | LM Studio TTL, load/unload, REST list API changes |
| `docs/reference/backend-api-parameters.md` | Parameter allowlists or backend differences change |
| `docs/resolution_tracker.md` | Promoting Assumed → Confirmed, or flagging Contaminated |
| `docs/lessons-learned.md` | Non-obvious runtime fixes (mandatory per `CLAUDE.md`) |
| `docs/research/cancel-interrupt-status.md` | Cancel/interrupt shipped vs gaps |
| `CLAUDE.md` | Pointers to prevention rules, template, and [`fresh-context-prevention-prompt.md`](fresh-context-prevention-prompt.md) |

---

## 11. Do not

- Use alarmist language ("everything is broken," "all research is trash").
- Treat backward audit as mandatory before every bugfix.
- Invalidate decisions (e.g. Ollama removal) without targeted evidence review.
- Copy GitHub issue numbers into code comments without date and status.
- Mark tracker rows `Confirmed` from docs-only reads of third-party summaries.

---

## Quick reference

| Need | Go to |
|------|--------|
| Fresh chat (normal work) | [`fresh-context-prevention-prompt.md`](fresh-context-prevention-prompt.md) |
| New research note | [`research-note-template.md`](research-note-template.md) |
| Example done right | [`textgen-lifecycle-verified.md`](textgen-lifecycle-verified.md) |
| Tracker status meanings | [`resolution_tracker.md`](../resolution_tracker.md) |
| Abandoned repo-wide inventory (archive) | [`docs/the-archive/2026-06-08-provenance-audit-handoff-abandoned.md`](../the-archive/2026-06-08-provenance-audit-handoff-abandoned.md) |
| Cancel shipped vs gaps | [`cancel-interrupt-status.md`](cancel-interrupt-status.md) |

**Trust hierarchy:** empirical → upstream @ pin → official docs → issue w/ date+status → wiki/blog/agent output.

**When in doubt:** research note + honest tracker status + verify what you change.
