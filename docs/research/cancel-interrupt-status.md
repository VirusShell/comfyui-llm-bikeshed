# Cancel / interrupt implementation status

**Created:** 2026-06-07  
**Last updated:** 2026-06-07  
**Status:** ComfyUI-side cooperative cancel **shipped** (commit `1006400`); host-side stop and cleanup **partial / gaps remain**.

---

## Scope

Tracking for **ComfyUI Cancel during LLM generation** in this pack — what is implemented, verified, and still open.

This is **not** the project-wide provenance audit. For citation rules and the episode that surfaced undated external claims during cancel research, see [`provenance-and-reverification.md`](provenance-and-reverification.md).

---

## Implemented (verified in code)

### ComfyUI interrupt polling and HTTP abort

- **`adapters/interrupt.py`** — loads `comfy.model_management.processing_interrupted` and `throw_exception_if_processing_interrupted` when running inside ComfyUI; falls back to direct `requests` outside ComfyUI (tests, scripts).
- **`interruptible_request()`** — runs the HTTP call in a daemon thread with transport-level `stream=True`, polls the ComfyUI flag every **250 ms** on the caller thread, and on cancel closes the in-flight `Response` and `Session`, then raises `InterruptProcessingException`.
- **`adapters/base.py`** — `_safe_post`, `_safe_get`, and `_request_with_errors` route through `interruptible_request()` when `comfy_interrupt_available()`; `check_before_request()` runs before each call.
- **`adapters/oai_compat.py`** — generation and lifecycle HTTP (chat completions, LM Studio model check/load, Textgen model info/load/unload) use `_safe_post` / `_safe_get` (wired in `1006400` for LM Studio `GET /api/v1/models` and Textgen `GET /v1/internal/model/info`).

**Commit:** `1006400` — `feat(adapters): honor ComfyUI Cancel during LLM HTTP` (2026-06-06). Incident narrative: [`docs/lessons-learned.md`](../lessons-learned.md) (2026-06-03 entry).

### What ComfyUI guarantees vs what this pack guarantees

| Layer | Guarantees |
|-------|------------|
| **ComfyUI** | Cancel sets a global interrupt flag (`interrupt_current_processing()`). It does **not** terminate in-flight HTTP, subprocesses, or worker threads in custom nodes. Nodes must poll cooperatively. |
| **This pack (shipped)** | Adapter HTTP used for generation and lifecycle management **unblocks the ComfyUI execution thread** on Cancel: polling detects the flag, aborts the client read, and propagates `InterruptProcessingException`. The workflow queue can proceed. |
| **This pack (not shipped)** | **Host inference stop** (GPU/VRAM work on LM Studio, Textgen, OpenAI, etc.), **lifecycle cleanup on interrupt** (unload / TTL follow-through), and **user-facing docs** on limits. |

### Test coverage (`tests/test_interrupt.py`)

| Test | What it verifies |
|------|------------------|
| `test_raises_before_request_when_already_interrupted` | Interrupt flag set before request → exception, no HTTP started. |
| `test_cancels_inflight_request` | Mock slow streamed response → flag set mid-flight → `resp.close()` called, `InterruptProcessingException` raised. |
| `test_safe_post_uses_direct_requests_outside_comfy` | When Comfy hooks absent, `_safe_post` uses plain `requests.post` (existing adapter test mocks keep working). |

**Not covered:** live ComfyUI queue run; real backend behavior after client disconnect; Textgen `stop-generation`; unload/TTL on interrupt; `_safe_get` adapter paths; `model_list.py` dropdown fetches.

---

## Not implemented / gaps

| Gap | Priority | Notes |
|-----|----------|-------|
| **Textgen `POST /v1/internal/stop-generation` on interrupt** | High — needs **[VERIFY]** | Maintainer reply on [textgen #4521](https://github.com/oobabooga/text-generation-webui/issues/4521) (closed 2023-11-09) suggests this route to stop in-flight generation; not wired in this pack. Endpoint auth, current upstream route, and effect on **non-streaming** `stream: false` chat calls are **unverified** here. |
| **No cleanup on interrupt** | Medium | `OAICompatAdapter.generate()` only runs unload (`_unload_model_*`) after a successful completion. Interrupt raises before that block — model can remain loaded on Textgen / LM Studio TTL path unchanged. |
| **`stream: false` in API body** | Medium (design constraint) | Chat payload always sets `"stream": False`. Transport uses streaming reads for cancel, but many hosts treat non-streaming completions as “run to completion server-side”; client disconnect may **not** stop inference. |
| **Model list endpoints not interruptible** | Low (acceptable) | `model_list.py` and server dropdown paths use bare `requests.get` / `requests.post` — short calls; not routed through `interruptible_request()`. |
| **User-facing README / node help** | Medium | No shipped documentation of cancel limits (Comfy unblocks vs host keeps generating). |

---

## Per-backend current state

| Backend | ComfyUI unblocks on Cancel? | Host stops inference on Cancel? | Next action |
|---------|----------------------------|-----------------------------------|-------------|
| **LM Studio** | Yes — via `_safe_post` interrupt polling | **Unknown / likely partial** — non-streaming chat + client abort; no explicit stop API wired | Empirical **[VERIFY]**; document limits in README |
| **Textgen** | Yes — same | **Unlikely from disconnect alone** — upstream maintainer documented `stop-generation` for OAI streaming cancel ([#4521](https://github.com/oobabooga/text-generation-webui/issues/4521)); pack does not call it | **[VERIFY]** route + auth; wire on interrupt; optional unload |
| **OpenAI** | Yes — same | **Do not assume** — cloud non-streaming request may complete or bill after client drop; not tested by this pack | Document expectation; no code change until scoped |
| **Generic OAI** | Yes — same | **Host-dependent** — same `stream: false` constraint | Document; verify per host if users report hangs |

---

## Open questions / [VERIFY] items

| Item | Source | Status |
|------|--------|--------|
| Does `POST /v1/internal/stop-generation` still exist and which key (`--api-key` vs `--admin-key`)? | [textgen #4521](https://github.com/oobabooga/text-generation-webui/issues/4521) comment, 2023-11-09; see provenance doc §3 | **[VERIFY]** — docs-only citation; read upstream `modules/api` or live `/docs` with access date |
| Does `stop-generation` affect **blocking** `/v1/chat/completions` with `stream: false`? | Pack always sends `stream: false` | **[VERIFY]** — empirical on running Textgen |
| Does LM Studio stop GPU work when the client closes a non-streaming chat connection? | Lessons-learned prevention note (2026-06-03) | **[VERIFY]** — empirical |
| Should interrupt trigger lifecycle unload (immediate vs defer vs skip)? | Product / VRAM policy | **Unresolved** — design choice |
| ComfyUI interrupt API stability | ComfyUI `comfy.model_management` | **Assumed** — matches lessons-learned fix; re-check on major ComfyUI upgrades |

---

## Recommended next steps (ordered, minimal)

1. **[VERIFY]** Textgen `POST /v1/internal/stop-generation` — upstream source read + one live cancel test; record in a research note row per [`provenance-and-reverification.md`](provenance-and-reverification.md).
2. **Wire stop-generation** in `interruptible_request()` or adapter interrupt handler when backend is Textgen and Comfy cancel fires (only after verify).
3. **Integration test** — mock or live Textgen: cancel mid-generation → assert stop endpoint called (unit) and/or host idle (manual QA).
4. **Interrupt cleanup policy** — decide unload-on-cancel vs leave-loaded; implement minimally if VRAM impact confirmed.
5. **User docs** — README + generation node help: Cancel stops the ComfyUI node; host may continue until stop API, timeout, or unload.

---

## Related

| Document / code | Role |
|-----------------|------|
| [`provenance-and-reverification.md`](provenance-and-reverification.md) | Citation standards; cancel research surfaced provenance gap (§3) |
| [`docs/lessons-learned.md`](../lessons-learned.md) | 2026-06-03 incident and fix narrative |
| [`adapters/interrupt.py`](../../adapters/interrupt.py) | Interrupt polling and HTTP close implementation |
| [`adapters/base.py`](../../adapters/base.py) | `_safe_post` / `_safe_get` integration |
| Commit `1006400` | Initial shipped cooperative cancel |
