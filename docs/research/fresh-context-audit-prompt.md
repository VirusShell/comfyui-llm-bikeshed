# Fresh-context audit prompt

**Copy everything below the horizontal rule into a new Cursor/Claude chat** to start or resume the project-wide provenance re-verification for `comfyui-llm-bikeshed`. This prompt is more directive than reading docs alone — it tells the agent what to do, in what order, and what not to assume.

---

## THE PROMPT

You are resuming **phased project-wide provenance re-verification** for the ComfyUI custom node pack **comfyui-llm-bikeshed**.

### Role & mission

Execute phased provenance re-verification across the repo — adapters, lifecycle, cancel/interrupt, API parameters, tracker rows, and research notes. This is **not** a cancel-only audit and **not** an assumption that all code or decisions are wrong.

**Core rule:** External research without dated provenance (URL, access date, issue/PR status, how verified) is **unverified** until re-checked against primary sources or empirical runs.

### Critical constraints

- **Remote is Gitea** — `http://192.168.1.163:3003/am_Vir/comfyui-llm-bikeshed.git`. **Not GitHub.** Do not use `gh`.
- **Branch:** `research/audit-and-cancel-tracking` (base: `master`). Confirm you are on this branch before changing code.
- **Read authoritative docs in order before changing code** (listed below).
- **Do not treat `Decided` or `Assumed` in `docs/resolution_tracker.md` as verified fact** — status reflects intent at write time, not proof.
- **Do not cite closed GitHub issues** without access date, open/closed/merged status, and whether the claim still applies.
- **Separate commits:** docs-only research updates vs code fixes. One concern per commit when practical.

### Authoritative docs (read in this order)

| Path | Purpose |
|------|---------|
| `docs/research/audit-handoff.md` | Tier 1 checklist, workflow, what's done vs pending |
| `docs/research/provenance-and-reverification.md` | Citation rules, tier framework, what not to assume |
| `docs/research/cancel-interrupt-status.md` | Shipped vs gaps for ComfyUI Cancel during generation |
| `docs/research/textgen-lifecycle-verified.md` | Upstream-verified Textgen routes, auth, load/unload |
| `docs/research/lm-studio-lifecycle-verified.md` | LM Studio TTL, load/unload, REST list API evidence |
| `docs/resolution_tracker.md` | Project decisions — status ≠ proof |
| `CLAUDE.md` | Project constraints; lessons-learned requirement |

### What triggered this

Cancel/interrupt research surfaced **undated, stale GitHub issue citations** treated as current upstream behavior without access date or status. That failure mode is **project-wide** — the same pattern may affect any research-derived decision (adapters, lifecycle, parameter allowlists, tracker rows, proposals).

### Current state (as of 2026-06-08)

**Branch `research/audit-and-cancel-tracking`:** ~3 commits ahead of `origin` (pushed research branch; not merged to `master`). Recent work includes Tier 1 handoff docs, provenance/cancel tracking, Textgen stop-generation wiring, LM Studio REST shape fixes, and lifecycle research notes.

**Tier 1 checklist (from `audit-handoff.md`):**

| Area | Status |
|------|--------|
| Interrupt polling + HTTP abort (`adapters/interrupt.py`) | **Verified** (code read 2026-06-07) |
| Safe request routing (`adapters/base.py`) | **Verified** |
| Generation + lifecycle HTTP (`adapters/oai_compat.py`) | **Verified** — Textgen stop-generation wired; LM Studio parse/unload fixed |
| Lifecycle nodes (`nodes/lifecycle.py`) | **Verified** |
| Textgen routes / auth / load-unload | **Verified** (cross-check `textgen-lifecycle-verified.md`) |
| LM Studio TTL / load / unload | **Verified** (docs + code); **live empirical QA [VERIFY]** |
| Cancel host-stop (Textgen `stop-generation`) | **Partial** — wired; empirical QA pending |

**First 3 ordered handoff tasks:** all marked done (2026-06-07). Tracker scan added surgical `[VERIFY]` flags on A-15, A-18, A-19, A-22, API-6.

**Open [VERIFY] items (next empirical work):**

1. Live Textgen: cancel mid-generation with `stream: false` → confirm GPU idle / generation stops after `stop-generation`.
2. Live LM Studio: client abort on non-streaming chat → does GPU work stop?
3. Interrupt cleanup policy (unload-on-cancel vs leave-loaded) — product decision, unresolved.

After Tier 1 empirical gaps are addressed or honestly documented, proceed to **Tier 2** per `provenance-and-reverification.md` (parameter allowlists, model list paths, backend fingerprinting).

### Your directives (ordered)

1. **Read all authoritative docs** listed above before editing code or promoting tracker rows.
2. **Confirm branch and remote** — `research/audit-and-cancel-tracking` on Gitea origin; not GitHub.
3. **Continue Tier 1 OR Tier 2** per provenance tiers — state explicitly what you are doing next based on the handoff checklist and `[VERIFY]` items above. Do not re-derive cancel status from old chat or undated issues; use `cancel-interrupt-status.md`.
4. **For each claim you rely on or update**, record: source URL, access date (ISO), issue/PR status if applicable, upstream version/commit, verified how (`code read` | `empirical` | `docs only`), and what it applies to.
5. **Update research docs in place** under `docs/research/` — no duplicate conflicting truths. Add `docs/lessons-learned.md` entries for non-obvious runtime surprises (required by `CLAUDE.md`).
6. **Mark work `[VERIFY]` until empirical** when evidence is docs-only or undated. Do not promote `resolution_tracker.md` rows to `Confirmed` without evidence matching the provenance standard.

### Out of scope

- **Textgen-rehaul lifecycle manager** — separate epic/design work
- **Full April 2026 static audit re-run** — `docs/thorough-audit-2026-04-27.md` is background reference only
- **Alarmist reframes** — do not declare all code, tracker rows, or shipped decisions invalid without targeted audit of that area's evidence
- **Tier 3 backlog** unless a Tier 1/2 change forces it

### Deliverables (each session)

- Updated `docs/research/*.md` notes with provenance tables (access date, status, verified how)
- `docs/research/cancel-interrupt-status.md` updated if interrupt behavior changes
- `docs/resolution_tracker.md` — flag, correct, or promote rows **only with evidence**
- `docs/lessons-learned.md` — new entry if runtime behavior surprised you
- Clear statement of what remains `[VERIFY]` and what tier is next

**Start by:** reading `docs/research/audit-handoff.md`, confirming git branch/remote, then stating the single next Tier 1 `[VERIFY]` task or Tier 2 entry point you will tackle.
