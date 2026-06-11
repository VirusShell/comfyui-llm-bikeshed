# Cancel / interrupt implementation status

**Created:** 2026-06-07  
**Last updated:** 2026-06-08  
**Status:** ComfyUI-side cooperative cancel **shipped** (commit `1006400`); Textgen host-side **stop-generation wired** (code read 2026-06-07, re-confirmed 2026-06-08); empirical host-stop QA **still open**; other cleanup **partial / gaps remain**.

---

## Scope

Tracking for **ComfyUI Cancel during LLM generation** in this pack — what is implemented, verified, and still open.

This is **not** the project-wide provenance audit. For decision-time gates and the episode that surfaced undated external claims during cancel research, see [`provenance-and-reverification.md`](provenance-and-reverification.md) § 8.

---

## Verification (code-read slice)

| Claim | Source | Access date | Verified how |
|-------|--------|-------------|--------------|
| ComfyUI interrupt flag + cooperative polling | `adapters/interrupt.py`, `docs/lessons-learned.md` (2026-06-03) | 2026-06-08 | code read |
| Textgen `stop-generation` route + API key gate | [`textgen-lifecycle-verified.md`](textgen-lifecycle-verified.md) | 2026-06-08 | code read |
| Pack wires `on_interrupt` for Textgen chat only | `adapters/oai_compat.py` | 2026-06-08 | code read |
| LM Studio has no stop API in pack | [`lm-studio-lifecycle-verified.md`](lm-studio-lifecycle-verified.md) | 2026-06-08 | code read + docs |

**Applies to:** `adapters/interrupt.py`, `adapters/base.py`, `adapters/oai_compat.py`, cancel/interrupt tracker notes.

---

## Falsifiers

- Textgen removes or renames `POST /v1/internal/stop-generation`, or moves it behind admin auth without pack update.
- ComfyUI changes interrupt API so `processing_interrupted()` is no longer the cooperative cancel signal.
- Empirical run shows Textgen `stream: false` chat ignores `stop_everything` despite client cancel + wired callback.

## Re-check triggers

- [ ] Changes to `adapters/interrupt.py`, `oai_compat.py` cancel path, or Textgen upstream auth/routes
- [ ] ComfyUI major upgrade
- [ ] Recorded empirical cancel QA in [`cancel-empirical-qa-handoff.md`](cancel-empirical-qa-handoff.md)

---

## Implemented (verified in code)

### ComfyUI interrupt polling and HTTP abort

- **`adapters/interrupt.py`** — loads `comfy.model_management.processing_interrupted` and `throw_exception_if_processing_interrupted` when running inside ComfyUI; falls back to direct `requests` outside ComfyUI (tests, scripts).
- **`interruptible_request()`** — runs the HTTP call in a daemon thread with transport-level `stream=True`, polls the ComfyUI flag every **250 ms** on the caller thread, and on cancel closes the in-flight `Response` and `Session`, then raises `InterruptProcessingException`.
- **`adapters/base.py`** — `_safe_post`, `_safe_get`, and `_request_with_errors` route through `interruptible_request()` when `comfy_interrupt_available()`; `check_before_request()` runs before each call.
- **`adapters/oai_compat.py`** — generation and lifecycle HTTP (chat completions, LM Studio model check/load, Textgen model info/load/unload) use `_safe_post` / `_safe_get` (wired in `1006400` for LM Studio `GET /api/v1/models` and Textgen `GET /v1/internal/model/info`). **Textgen cancel:** chat completions pass `on_interrupt` → `POST /v1/internal/stop-generation` (API key when configured).

**Commit:** `1006400` — `feat(adapters): honor ComfyUI Cancel during LLM HTTP` (2026-06-06). Incident narrative: [`docs/lessons-learned.md`](../lessons-learned.md) (2026-06-03 entry). Textgen stop-generation wiring: 2026-06-07 (Tier 2 runtime verification).

### What ComfyUI guarantees vs what this pack guarantees

| Layer | Guarantees |
|-------|------------|
| **ComfyUI** | Cancel sets a global interrupt flag (`interrupt_current_processing()`). It does **not** terminate in-flight HTTP, subprocesses, or worker threads in custom nodes. Nodes must poll cooperatively. |
| **This pack (shipped)** | Adapter HTTP used for generation and lifecycle management **unblocks the ComfyUI execution thread** on Cancel: polling detects the flag, aborts the client read, and propagates `InterruptProcessingException`. The workflow queue can proceed. **Textgen:** `POST /v1/internal/stop-generation` is called on cancel during chat completions (API key when configured). |
| **This pack (not shipped)** | **Host inference stop** for LM Studio / OpenAI / generic OAI, **lifecycle cleanup on interrupt** (unload / TTL follow-through), and **user-facing docs** on limits. |

### Test coverage (`tests/test_interrupt.py`)

| Test | What it verifies |
|------|------------------|
| `test_raises_before_request_when_already_interrupted` | Interrupt flag set before request → exception, no HTTP started. |
| `test_cancels_inflight_request` | Mock slow streamed response → flag set mid-flight → `resp.close()` called, `InterruptProcessingException` raised. |
| `test_calls_on_interrupt_callback` | Cancel mid-flight → optional `on_interrupt` callback invoked before exception. |
| `test_safe_post_uses_direct_requests_outside_comfy` | When Comfy hooks absent, `_safe_post` uses plain `requests.post` (existing adapter test mocks keep working). |

**Not covered:** live ComfyUI queue run; real backend behavior after client disconnect; Textgen `stop-generation` called from `OAICompatAdapter.generate` (only `interruptible_request` callback tested); unload/TTL on interrupt; `_safe_get` adapter paths; `model_list.py` dropdown fetches.

**2026-06-08 code re-read:** `oai_compat.py` still sets `on_interrupt` for `text_gen_webui` only; `_stop_generation_textgen` uses bare `requests.post` to `/v1/internal/stop-generation` with API bearer headers. LM Studio / OpenAI paths have no `on_interrupt` hook.

---

## Not implemented / gaps

| Gap | Priority | Notes |
|-----|----------|-------|
| **No cleanup on interrupt** | Medium | `OAICompatAdapter.generate()` only runs unload (`_unload_model_*`) after a successful completion. Interrupt raises before that block — model can remain loaded on Textgen / LM Studio TTL path unchanged. LM Studio / Textgen unload paths use **bare `requests.post`** (not interruptible) — intentional for post-success cleanup only. |
| **`stream: false` in API body** | Medium (design constraint) | Chat payload always sets `"stream": False`. Transport uses streaming reads for cancel, but many hosts treat non-streaming completions as “run to completion server-side”; client disconnect may **not** stop inference. |
| **Model list endpoints not interruptible** | Low (acceptable) | `model_list.py` and server dropdown paths use bare `requests.get` / `requests.post` — short calls; not routed through `interruptible_request()`. |
| **User-facing README / node help** | Medium | No shipped documentation of cancel limits (Comfy unblocks vs host keeps generating). |

---

## Per-backend current state

| Backend | ComfyUI unblocks on Cancel? | Host stops inference on Cancel? | Next action |
|---------|----------------------------|-----------------------------------|-------------|
| **LM Studio** | Yes — via `_safe_post` interrupt polling | **Unknown / likely partial** — non-streaming chat + client abort; no explicit stop API wired | Empirical **[VERIFY]**; document limits in README |
| **Textgen** | Yes — same | **Stop API wired** — `POST /v1/internal/stop-generation` on cancel (API key); sets `shared.stop_everything` upstream. **Empirical [VERIFY]** on live instance still recommended for `stream: false` chat. | Live cancel QA; document in README |
| **OpenAI** | Yes — same | **Do not assume** — cloud non-streaming request may complete or bill after client drop; not tested by this pack | Document expectation; no code change until scoped |
| **Generic OAI** | Yes — same | **Host-dependent** — same `stream: false` constraint | Document; verify per host if users report hangs |

---

## Open questions / [VERIFY] items

| Item | Source | Status |
|------|--------|--------|
| Does `POST /v1/internal/stop-generation` still exist and which key (`--api-key` vs `--admin-key`)? | https://github.com/oobabooga/textgen/blob/main/modules/api/script.py (access 2026-06-07) | **Confirmed** — route exists; `check_key` → API key |
| Does `stop-generation` affect **blocking** `/v1/chat/completions` with `stream: false`? | Upstream sets `shared.stop_everything`; generation loop checks it | **Code read confirmed**; **empirical [VERIFY]** on live Textgen still open |
| Does LM Studio stop GPU work when the client closes a non-streaming chat connection? | Lessons-learned prevention note (2026-06-03) | **[VERIFY]** — empirical |
| Should interrupt trigger lifecycle unload (immediate vs defer vs skip)? | Product / VRAM policy | **Unresolved** — design choice |
| ComfyUI interrupt API stability | ComfyUI `comfy.model_management` | **Assumed** — matches lessons-learned fix; re-check on major ComfyUI upgrades |

---

## Recommended next steps (ordered, minimal)

1. **Empirical [VERIFY]** — live Textgen: cancel mid-generation with `stream: false` → confirm GPU idle / generation stops. **Procedure:** [`cancel-empirical-qa-handoff.md`](cancel-empirical-qa-handoff.md).
2. **Empirical [VERIFY]** — live LM Studio: same cancel scenario; document whether GPU work stops (no stop API in pack). **Procedure:** same doc.
3. **Integration test** — mock Textgen: cancel mid-generation → assert `POST …/stop-generation` called (unit); complements manual QA.
4. **Interrupt cleanup policy** — decide unload-on-cancel vs leave-loaded; implement minimally if VRAM impact confirmed.
5. **User docs** — README + generation node help: Cancel stops the ComfyUI node; host may continue until stop API, timeout, or unload.

---

## Related

| Document / code | Role |
|-----------------|------|
| [`provenance-and-reverification.md`](provenance-and-reverification.md) | Decision-time gates; cancel research surfaced write-time gap (§ 8) |
| [`cancel-empirical-qa-handoff.md`](cancel-empirical-qa-handoff.md) | Live cancel QA protocol (subsidiary; human-run) |
| [`audit-handoff.md`](audit-handoff.md) | Abandoned provenance audit (archive pointer) |
| [`docs/lessons-learned.md`](../lessons-learned.md) | 2026-06-03 incident and fix narrative |
| [`adapters/interrupt.py`](../../adapters/interrupt.py) | Interrupt polling and HTTP close implementation |
| [`adapters/base.py`](../../adapters/base.py) | `_safe_post` / `_safe_get` integration |
| [`lm-studio-lifecycle-verified.md`](lm-studio-lifecycle-verified.md) | LM Studio TTL / load / unload upstream evidence |
