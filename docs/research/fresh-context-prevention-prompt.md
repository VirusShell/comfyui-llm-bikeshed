# Fresh-context prompt — decision-time prevention (default)

> **Use this prompt** for normal feature work, bugfixes, and research in **comfyui-llm-bikeshed**.

You are working on the ComfyUI custom node pack **comfyui-llm-bikeshed**.

## Mission

Apply **decision-time prevention** before external claims become durable project truth. Do **not** treat undated GitHub issues, wiki pages, or tracker `Decided`/`Assumed` rows as verified fact without traceable evidence.

## Read first (in order)

| Doc | Why |
|-----|-----|
| [`provenance-and-reverification.md`](provenance-and-reverification.md) | **Gate A–C:** research notes, tracker status, shipping behavior |
| [`research-note-template.md`](research-note-template.md) | Structure for new/updated `docs/research/*.md` (gold example: [`textgen-lifecycle-verified.md`](textgen-lifecycle-verified.md)) |
| [`resolution_tracker.md`](../resolution_tracker.md) | § Status definitions — status ≠ proof; use `[VERIFY]` when evidence is incomplete |
| [`CLAUDE.md`](../../CLAUDE.md) | Pack scope, shipped backends, mandatory lessons-learned rule |

## Before you cite or ship

1. **External fact** → source URL, access date (`YYYY-MM-DD`), verified how (`code read` / `empirical` / `docs only`), applies-to files/tracker IDs.
2. **Tracker promotion** → matching research note row; `docs only` alone is **not** enough for **Confirmed**.
3. **Textgen routes/auth** → read [`textgen-lifecycle-verified.md`](textgen-lifecycle-verified.md).
4. **LM Studio lifecycle** → read [`lm-studio-lifecycle-verified.md`](lm-studio-lifecycle-verified.md).
5. **Runtime surprise with non-obvious root cause** → entry in [`docs/lessons-learned.md`](../lessons-learned.md) per `CLAUDE.md`.

## Constraints

- Re-verify **sources for the path you change** — do not block urgent fixes on a full-repo audit.
- Cancel empirical QA is subsidiary — [`cancel-empirical-qa-handoff.md`](cancel-empirical-qa-handoff.md) — not the default session framing.
- The backward provenance inventory was **abandoned** (2026-06-11); see [`audit-handoff.md`](audit-handoff.md).

## Start by

State which **decision-time gate** (A, B, or C from `provenance-and-reverification.md`) applies to the user's task, then proceed.
