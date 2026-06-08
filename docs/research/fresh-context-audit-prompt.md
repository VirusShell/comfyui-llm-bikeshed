You are resuming **project-wide provenance re-verification** for the ComfyUI custom node pack **comfyui-llm-bikeshed**.

## Role & mission

**Primary mission:** Determine whether the project — docs, design decisions, tracker rows, and code assumptions — was built on bad, stale, or unverified external information. Inventory claims, check evidence, flag gaps, and re-fetch upstream sources where provenance is weak.

Cancel work **surfaced** a provenance failure pattern; fixing that pattern is **project-wide**. Do **not** assume all code or decisions are wrong — audit evidence per claim. **Empirical cancel QA is not part of this prompt** — see `docs/research/cancel-empirical-qa-handoff.md`.

**Core rule:** External research is **unverified** until re-checked. The failure mode is treating **old** sources as current fact — without checking **when they were posted** or, where relevant, **open/closed/merged status** — not merely forgetting to log when you read them.

## Critical constraints

- **Remote is Gitea** — `http://192.168.1.163:3003/am_Vir/comfyui-llm-bikeshed.git`. **Not GitHub.** Do not use `gh`.
- **Branch:** `research/audit-and-cancel-tracking` (base: `master`). Confirm you are on this branch before changing code.
- **Read authoritative docs in order before changing code** (listed below).
- **Do not treat `Decided` or `Assumed` in `docs/resolution_tracker.md` as verified fact** — status reflects intent at write time, not proof.
- **Source age and status:** See `docs/research/provenance-and-reverification.md` § 4 before treating external material as current fact.

## Authoritative docs (read in this order)

| Path | Purpose |
|------|---------|
| `docs/research/audit-handoff.md` | **Primary** — checklist, next tasks, workflow |
| `docs/research/provenance-and-reverification.md` | Citation rules, tier framework, provenance standard |
| `docs/resolution_tracker.md` | Project decisions — status ≠ proof |

Other conditional reads: `docs/research/audit-handoff.md` § Start here.

## Background & current state

See `docs/research/audit-handoff.md` § Why agents drifted to cancel QA. For git/branch status, Tier 1/2 tables, and session log, see the same doc.

## Directives (ordered)

1. **Read `docs/research/audit-handoff.md` and `docs/research/provenance-and-reverification.md`** before editing code or promoting tracker rows.
2. **Start with Tier 1 provenance work** per `docs/research/audit-handoff.md` § Next work.
3. **Per-claim provenance:** `docs/research/provenance-and-reverification.md` § 4; updates, `[VERIFY]`, and `docs/lessons-learned.md` per `docs/research/audit-handoff.md` § Outputs and `CLAUDE.md`.

## Out of scope

- **Textgen-rehaul lifecycle manager** — separate epic/design work
- **Full April 2026 static audit re-run** — `docs/thorough-audit-2026-04-27.md` is background reference only
- **Alarmist reframes** — do not declare all code, tracker rows, or shipped decisions invalid without targeted audit of that area's evidence
- **Empirical cancel QA** — human-run protocol in `docs/research/cancel-empirical-qa-handoff.md`, not this session

## Deliverables

See `docs/research/audit-handoff.md` § Outputs.

**Start by:** reading `docs/research/audit-handoff.md`, confirming git branch/remote, then stating the **single next Tier 1 provenance task** from § Next work.
