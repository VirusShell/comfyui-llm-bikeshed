# External ComfyUI custom-node reference corpus — status

**Created:** 2026-06-08  
**Status:** Inventory + disposition — **not** authoritative for this pack's runtime decisions. Decision-time gates: [`provenance-and-reverification.md`](provenance-and-reverification.md).  
**Scope:** Off-repo research mirror at `D:\ai\tmp\comfyui-custom-nodes-research\` and how it relates to in-repo docs.

---

## Summary

| Question | Answer |
|----------|--------|
| Is the path in runtime code? | **No** — docs/agent guidance only |
| Is it still on disk (author's machine)? | **Yes** as of 2026-06-08 — last touched Feb–Mar 2026 |
| Is it authoritative for this project? | **No** — project-specific findings live in-repo (see below) |
| What action is pending? | **Unresolved (DOC-1)** — vendor into repo, drop pointers, or archive |

---

## What it was

A **scratch research corpus** produced in a Claude Code session on **2026-02-26**. It summarizes official ComfyUI custom-node documentation from [docs.comfy.org/custom-nodes](https://docs.comfy.org/custom-nodes/) into numbered markdown files plus a ledger.

**Session artifacts** (same parent folder, not in this repo):

| Path | Role |
|------|------|
| `D:\ai\tmp\response.txt` | Completion summary: 11 docs + `LEDGER.md`, ~95% official-doc coverage; open questions about template-repo and community deep-dives |
| `D:\ai\tmp\response-split.txt` | Follow-up recommending splits for `04`, `05`, `06` — **splits were never applied** |
| `D:\ai\tmp\.claude\settings.local.json` | Only `WebFetch(domain:docs.comfy.org)` — confirms one-off doc-fetch session |

**Corpus contents** (`D:\ai\tmp\comfyui-custom-nodes-research\`):

| File | Notes |
|------|-------|
| `LEDGER.md` | Master index; created 2026-02-26 |
| `01-overview.md` … `11-i18n-and-context-menu-migration.md` | Official-doc distillations; source date 2026-02-26 |
| `12-lessons-learned.md` | Project-specific pitfalls from building this pack; updated 2026-03-15 |

**Never completed** (per session transcripts): splitting large files (`05`, `06`, optionally `04`); template-repo deep-dives; community-source research (issues, Reddit, etc.).

---

## In-repo replacements (use these instead)

For **this pack's** decisions and patterns, prefer:

| Need | In-repo location |
|------|------------------|
| Platform behavior (P-9, P-10, COMBO, errors) | `docs/reference/comfyui-platform-findings.md` |
| Copy-paste implementation patterns | `docs/reference/implementation-patterns.md` |
| Backend parameters | `docs/reference/backend-api-parameters.md` |
| Timestamped evidence / citations | `docs/the-archive/` |
| Runtime surprises | `docs/lessons-learned.md` |
| Textgen / LM Studio lifecycle (verified) | `docs/research/textgen-lifecycle-verified.md`, `docs/research/lm-studio-lifecycle-verified.md` |
| Provenance rules | `docs/research/provenance-and-reverification.md` |
| Ralph spec research (gitignored) | `specs/comfyui-llm-bikeshed/research.md` |

The external corpus remains useful only as a **broad ComfyUI custom-node cheat sheet** until vendored or replaced by live official docs.

---

## Stale pointers in this repo (as of 2026-06-08)

| Location | Issue |
|----------|-------|
| `CLAUDE.md` § ComfyUI Custom Node Reference | Hardcoded `D:\ai\tmp\…` path + file table — **updated 2026-06-08** to point here |
| `docs/reference/implementation-patterns.md` Sources | Same hardcoded path — **updated 2026-06-08** |
| `docs/the-archive/2026-05-11-comfyui-input-validation-and-connection-patterns.md` R-2026-05-11-007 | Cites local mirror path for provenance — **kept** (historical capture); see note in that entry |
| `docs/resolution_tracker.md` P-1 | References `05-backend-advanced.md` without path — means external corpus file name, not in-repo |

---

## Loose ends

| Item | Status |
|------|--------|
| `comfyui-node-standards.md` | Referenced in old `CLAUDE.md` as "project memory" — **not in this repo**, not in external corpus; treat as **lost / never committed** |
| Machine-specific path | **Not portable** — do not add new references to `D:\ai\tmp\` |
| Vendoring into `docs/reference/` | **Open** — owner decision (DOC-1) |

---

## Disposition options (DOC-1)

1. **Vendor** — copy corpus (or subset) into e.g. `docs/reference/comfyui-custom-nodes/`; update archive provenance URLs to in-repo paths.
2. **Drop pointer** — rely on [docs.comfy.org](https://docs.comfy.org/custom-nodes/) + existing `docs/reference/`; delete or ignore external folder.
3. **Hybrid** — vendor only `12-lessons-learned.md`-style project bits (already largely in `docs/lessons-learned.md`); link upstream for generic API reference.

---

## Applies to

- `CLAUDE.md` — agent onboarding
- `docs/resolution_tracker.md` — row DOC-1
- Future doc hygiene; no adapter or node code
