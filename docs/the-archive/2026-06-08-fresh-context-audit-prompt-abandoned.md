> **Status: ABANDONED** (2026-06-11). Archived copy of the backward-inventory paste prompt. For normal work, use [`fresh-context-prevention-prompt.md`](../research/fresh-context-prevention-prompt.md) instead.

You are resuming **optional project-wide provenance inventory** for the ComfyUI custom node pack **comfyui-llm-bikeshed**.

## Role & mission

**Primary mission (when this prompt is used):** Inventory existing claims across docs, tracker rows, and code assumptions; flag weak provenance; re-fetch upstream where needed. **Not** the default framing for new features or bugfixes.

**Default mission for most sessions:** **Decision-time prevention** — before writing research, promoting tracker status, or shipping behavior, apply gates in `docs/research/provenance-and-reverification.md`. Do not treat undated issues or `Decided` rows as verified fact.

Cancel work **surfaced** a write-time failure pattern (old issue cited as current fact). Prevention stops recurrence; backward inventory cleans up what already exists. Do **not** assume all code or decisions are wrong — check evidence per claim. **Empirical cancel QA is not part of this prompt** — see `docs/research/cancel-empirical-qa-handoff.md`.

**Core rule:** External research is **unverified** until recorded with access date, source status, and verified how — at the moment it influences durable project truth.

## Critical constraints

- **Remote (historical):** private Gitea instance (redacted); target host is GitHub.
- **Branch:** `research/audit-and-cancel-tracking` (base: `master`). Confirm you are on this branch before changing code.
- **Read authoritative docs in order before changing code** (listed below).
- **Do not treat `Decided` or `Assumed` in `docs/resolution_tracker.md` as verified fact** — status reflects intent at write time, not proof.
- **Source age and status:** See `docs/research/provenance-and-reverification.md` § 3 (write-time citation standard) before treating external material as current fact.

## Authoritative docs (read in this order)

| Path | Purpose |
|------|---------|
| `docs/research/provenance-and-reverification.md` | **Primary for new work** — decision-time gates, trust hierarchy, template link |
| `docs/research/research-note-template.md` | Copy-paste structure for new research notes |
| `docs/research/audit-handoff.md` | **Secondary** — backward inventory checklist (this prompt only) |
| `docs/resolution_tracker.md` | Project decisions — see § Status definitions; status ≠ proof |

Other conditional reads: `docs/research/audit-handoff.md` § Start here.

## Background & current state

See `docs/research/audit-handoff.md` § Why agents drifted to cancel QA. For git/branch status, Tier 1/2 tables, and session log, see the same doc.

## Directives (ordered)

1. **Read `docs/research/provenance-and-reverification.md`** — apply decision-time gates for any new cites or status promotions.
2. **If and only if doing backward inventory:** read `docs/research/audit-handoff.md` and start Tier 1 per § Next work.
3. **Per-claim provenance:** research note template + verified how; `[VERIFY]` in tracker Notes; `docs/lessons-learned.md` per `CLAUDE.md` when runtime fixes reveal non-obvious causes.

## Out of scope

- **Textgen-rehaul lifecycle manager** — separate epic/design work
- **Full April 2026 static audit re-run** — `docs/thorough-audit-2026-04-27.md` is background reference only
- **Alarmist reframes** — do not declare all code, tracker rows, or shipped decisions invalid without targeted audit of that area's evidence
- **Empirical cancel QA** — human-run protocol in `docs/research/cancel-empirical-qa-handoff.md`, not this session

## Deliverables

See `docs/research/audit-handoff.md` § Outputs.

**Start by (backward inventory only):** reading `docs/research/audit-handoff.md`, confirming git branch/remote, then stating the **single next Tier 1 task** from § Next work. **Otherwise:** read `provenance-and-reverification.md` and state which decision-time gate applies to the user's task.
