# Cancel empirical QA — operational handoff

> Decision-time prevention for new claims: [`provenance-and-reverification.md`](provenance-and-reverification.md).

**Created:** 2026-06-08  
**Status:** Protocol ready; **no empirical runs recorded** as of 2026-06-08. Independent of the abandoned provenance audit (2026-06-11).

---

## Why this document exists

**Subsidiary track only — not the project-wide provenance audit.**

Prior audit handoffs listed live Textgen/LM Studio cancel QA as **priority 1 “next work.”** Fresh agents then treated the whole session as cancel QA instead of the broader provenance sweep (claim inventory, tracker contamination, doc/code alignment).

This doc **isolates** human-run empirical cancel verification so it is not lost. The project-wide provenance audit was **abandoned** (2026-06-11); see [`audit-handoff.md`](audit-handoff.md).

Cancel research also **surfaced** the provenance failure pattern documented in [`provenance-and-reverification.md`](provenance-and-reverification.md) § 8 — that episode is context, not the scope of this handoff.

---

## Relationship to other docs

| Document | Role |
|----------|------|
| [`cancel-interrupt-status.md`](cancel-interrupt-status.md) | **Shipped vs gaps** — what the pack implements, code-read verification, per-backend table, open `[VERIFY]` items. Update when behavior or test coverage changes. |
| **This document** | **How to run live cancel QA** — step-by-step protocol, evidence to record, when to execute. |
| [`audit-handoff.md`](audit-handoff.md) | Abandoned provenance audit — pointer to archive only. |
| [`textgen-lifecycle-verified.md`](textgen-lifecycle-verified.md) | Upstream Textgen routes, auth split, `stop-generation` source evidence. |
| [`lm-studio-lifecycle-verified.md`](lm-studio-lifecycle-verified.md) | LM Studio TTL, load/unload; notes no stop API in pack. |

**Division of labor:** `cancel-interrupt-status.md` = **code-read + product status**; this doc = **empirical runs** that close `[VERIFY]` rows where live backend behavior is unknown.

---

## When to do this

| Do | Do not |
|----|--------|
| When closing `[VERIFY]` cancel rows or validating interrupt behavior before a release | **Instead of** ad-hoc cancel testing without recording evidence |
| When a human has GPU + live Textgen and/or LM Studio + ComfyUI | When only code-read or docs-only verification is needed — use `cancel-interrupt-status.md` |
| When explicitly closing `[VERIFY]` on cancel/host-stop behavior | As the default “start here” for a fresh audit chat |

**Blocker:** Requires a machine with GPU, running backends, and ComfyUI — not available in typical agent-only environments.

---

## Verified in code (2026-06-08) vs still needs live runs

### Verified in code (no live backend required)

| Area | Evidence | Location |
|------|----------|----------|
| ComfyUI interrupt polling + HTTP abort | Re-read 2026-06-07, 2026-06-08 | `adapters/interrupt.py`, `adapters/base.py` |
| Textgen `on_interrupt` → `POST /v1/internal/stop-generation` | Wired; upstream route confirmed 2026-06-07 | `adapters/oai_compat.py` (~220–224, `_stop_generation_textgen` ~439–453) |
| LM Studio lifecycle REST parse + unload | Fixed 2026-06-07; re-read 2026-06-08 | `adapters/oai_compat.py` |
| Unit tests for interrupt callback | Mock tests pass | `tests/test_interrupt.py` |

**Commit:** `1006400` — `feat(adapters): honor ComfyUI Cancel during LLM HTTP` (2026-06-06).

### Still needs empirical `[VERIFY]`

| Question | Backend | Why live run matters |
|----------|---------|----------------------|
| Does `stop-generation` stop **blocking** `/v1/chat/completions` with `stream: false`? | Textgen | Pack always sends `stream: false` in API body; upstream sets `shared.stop_everything` but host may still run to completion |
| Does client abort stop GPU work on non-streaming chat? | LM Studio | No stop API wired in pack; outcome documents user-facing limits only |
| Full load → generate → cancel → unload chain | Textgen, LM Studio | Tracker rows A-15, A-18, A-19, A-22 carry empirical `[VERIFY]` flags |

Record outcomes in [`cancel-interrupt-status.md`](cancel-interrupt-status.md) and promote tracker rows only with evidence per [`provenance-and-reverification.md`](provenance-and-reverification.md) § 2 (Gate B).

---

## Empirical QA protocol

Run on a machine with GPU + live backends. Record results in [`cancel-interrupt-status.md`](cancel-interrupt-status.md).

### Textgen — cancel stops host inference

| Step | Action | Pass criterion |
|------|--------|----------------|
| 1 | Start Textgen with `--api` and `--api-key` (note version / commit in results) | Server reachable at configured URL |
| 2 | Load a slow model; workflow: Provider (Textgen lifecycle ON) → Generate with high `max_tokens`, `stream: false` in payload (pack default) | Generation starts; GPU utilization rises |
| 3 | Click ComfyUI **Cancel** mid-generation | ComfyUI queue unblocks (no hang) |
| 4 | Observe Textgen logs / `nvidia-smi` (or equivalent) within ~30 s | GPU utilization drops; no new tokens in Textgen UI |
| 5 | Optional: packet capture or Textgen access log | `POST /v1/internal/stop-generation` received before client disconnect |

**Stop route source:** `oobabooga/textgen` `modules/api/script.py` — upstream access 2026-06-07 ([`textgen-lifecycle-verified.md`](textgen-lifecycle-verified.md)). Pack wiring: `oai_compat.py` lines ~220–224, `_stop_generation_textgen` ~439–453.

### LM Studio — client abort vs GPU work

| Step | Action | Pass criterion |
|------|--------|----------------|
| 1 | Start LM Studio local server; note app version | Server reachable |
| 2 | Load model; Generate with high `max_tokens`, lifecycle TTL set (e.g. 30 s) | Generation starts; GPU busy |
| 3 | Cancel mid-generation | ComfyUI unblocks |
| 4 | Observe GPU / LM Studio inference panel | Document whether inference stops or runs to completion |

**No stop API wired** for LM Studio (unlike Textgen). Outcome documents user-facing limits only — not a code failure unless product scopes a fix.

### Evidence to record (per provenance standard)

For each run: source URL (if citing upstream behavior), **source date** (backend version / issue status), access date (when you ran QA), verified how = `empirical`, applies to (tracker row or `cancel-interrupt-status.md` section).

---

## Related code and tracker rows

| Item | Reference |
|------|-----------|
| Interrupt implementation | [`adapters/interrupt.py`](../../adapters/interrupt.py), [`adapters/base.py`](../../adapters/base.py) |
| Textgen stop + lifecycle | [`adapters/oai_compat.py`](../../adapters/oai_compat.py) |
| Lifecycle nodes | [`nodes/lifecycle.py`](../../nodes/lifecycle.py) |
| Incident narrative | [`docs/lessons-learned.md`](../lessons-learned.md) (2026-06-03 entry) |
| Tracker `[VERIFY]` rows | A-15, A-18, A-19, A-22 in [`resolution_tracker.md`](../resolution_tracker.md) |

---

## Follow-ups after empirical QA (optional)

1. **Integration test** — mock Textgen: cancel mid-generation → assert `POST …/stop-generation` called (strengthens wiring proof without live backend).
2. **Interrupt cleanup policy** — unload-on-cancel vs leave-loaded (human decision; VRAM vs latency).
3. **User docs** — README + generation node help: Cancel stops the ComfyUI node; host may continue until stop API, timeout, or unload.

See [`cancel-interrupt-status.md`](cancel-interrupt-status.md) § Recommended next steps for ordered minimal list.
