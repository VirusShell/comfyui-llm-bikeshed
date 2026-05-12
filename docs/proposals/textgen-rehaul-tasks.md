# Textgen Rehaul Implementation Checklist

This checklist is intentionally separated from active project specs/docs.  
It is scoped to implementing `docs/proposals/textgen-rehaul.md`.

**Product direction — read first:** [`product-direction-and-scope.md`](product-direction-and-scope.md) (Textgen-first priority, lifecycle full rethink, planned Ollama removal as documentation-stage intent with code removal as follow-up, llama.cpp deferred).

**Note:** Rollout **phases** in `textgen-rehaul.md` (schema → manager → diagnostics → optional utilities) are a product rollout story; **task phase numbers here** (Phase 1–8) are implementation ordering. They are **not** 1:1 (e.g. proposal “Phase 4” optional utility nodes map to the optional subsection below, not necessarily “Phase 4” here).

- [ ] **Lifecycle redesign gate:** Before implementing phases that change Textgen lifecycle schema, adapters, or a runtime lifecycle manager, **re-read** `product-direction-and-scope.md` and the *Status & scope* section of `textgen-rehaul.md`. Lifecycle tasks here remain **subject to redesign** and may be superseded or heavily revised by a broader lifecycle rethink.

## Phase 1 - Schema and Node Contract (non-breaking)

- [ ] **Product / defaults (A-18 alignment):** Lock shipped widget defaults and legacy `{"type":"text_gen_webui"}` mapping to proposal VRAM-first policy: `unload_policy = immediate`; `after_idle` + `idle_seconds` only when the user opts in. Update `docs/resolution_tracker.md` A-18 only if tracker wording conflicts after this lock-in.
- [ ] Update `nodes/lifecycle.py` (`LLMLifecycleTextGenWebUI`) to emit policy-based payload when enabled:
  - [ ] `type`
  - [ ] `enabled`
  - [ ] `load_policy`
  - [ ] `unload_policy`
  - [ ] `idle_seconds`
  - [ ] `switch_policy`
- [ ] Keep backward-compatible OFF behavior (`{}` lifecycle dict).
- [ ] Add/adjust widgets in `LLMLifecycleTextGenWebUI.INPUT_TYPES`:
  - [ ] `manage_model_memory` (BOOLEAN)
  - [ ] `unload_policy` (COMBO)
  - [ ] `idle_seconds` (INT)
  - [ ] `load_policy` (COMBO)
  - [ ] `switch_policy` (COMBO)
- [ ] Ensure ComfyUI rendering reliability is preserved (at least one required widget remains).
- [ ] Keep LM Studio lifecycle node unchanged unless shared helpers are introduced.

## Phase 2 - Adapter Lifecycle Policy Parsing

- [ ] Add lifecycle parser in `adapters/oai_compat.py` to normalize Textgen lifecycle payloads.
- [ ] Implement compatibility mapping:
  - [ ] Legacy `{"type": "text_gen_webui"}` -> default policy values.
  - [ ] Empty dict / missing lifecycle -> lifecycle disabled.
- [ ] Ensure lifecycle type mismatch behavior remains unchanged (informational log + skip management).
- [ ] Keep existing behavior for non-Textgen backends untouched.

## Phase 3 - Textgen Runtime Lifecycle Manager

- [ ] Add per-endpoint Textgen lifecycle manager in `adapters/oai_compat.py` (or adjacent module if extracted).
- [ ] Key manager state by normalized endpoint identity (backend + URL).
- [ ] Introduce concurrency controls:
  - [ ] Per-endpoint lock around load/switch/unload mutation calls.
  - [ ] In-flight request counter.
  - [ ] Last activity timestamp.
  - [ ] Optional last-known loaded model cache hint.
- [ ] Add unload timer orchestration for `after_idle` policy:
  - [ ] Schedule timer at chain end.
  - [ ] Cancel/reschedule on new request.
  - [ ] Guard timer unload by in-flight checks.
- [ ] **Risk #3 (timer vs lock):** Per-endpoint `threading.RLock` — keep shared state mutations under the lock; run HTTP (`requests`) outside the lock; timer callback acquires lock, re-checks `in_flight == 0` and idle elapsed before unload HTTP.
- [ ] **Risk #4 (`model/info` cache):** Short TTL hint cache (~5 s default), invalidate on 4xx/5xx from generate/load paths; optional info log when stale cache may explain surprising behavior.

## Phase 4 - Request Flow Policy Enforcement

- [ ] Before generation, enforce `load_policy` and `switch_policy`:
  - [ ] `ensure_loaded`
  - [ ] `require_preloaded`
  - [ ] `auto_switch`
  - [ ] `error_if_other_model_loaded`
- [ ] Maintain existing chat request path (`/v1/chat/completions`) and option allowlists.
- [ ] At request completion, combine chain signal and policy:
  - [ ] If `skip_unload == True`, never unload this call.
  - [ ] Else enforce `unload_policy` (`immediate`, `after_idle`, `never`).
- [ ] Preserve auth header behavior for Textgen internal routes (`admin_key` fallback to `api_key`).

## Phase 5 - Generation Node Contract Validation

- [ ] **Risk #5 (introspection drift):** Replace hardcoded `GENERATION_CLASS_TYPES` with a registry or class marker; add a test that every `NODE_CLASS_MAPPINGS` class whose `RETURN_TYPES` includes `LLM_META` is discoverable by `has_downstream_gen_node` (or equivalent chain logic).
- [ ] Confirm no interface changes needed in `nodes/generation.py`:
  - [ ] Keep hidden `PROMPT` / `UNIQUE_ID` inputs.
  - [ ] Keep `skip_unload = has_downstream_gen_node(...)`.
  - [ ] Keep adapter call signature stable.
- [ ] Confirm `graph/introspection.py` logic remains valid for this rehaul.

## Phase 6 - Logging and Error Quality

- [ ] Add structured info logs in `adapters/oai_compat.py` for:
  - [ ] Selected lifecycle policy
  - [ ] Chain-based unload skip decisions
  - [ ] Model switch/load decisions
  - [ ] Unload path (immediate, delayed, never)
- [ ] Add explicit errors for strict policy violations:
  - [ ] `require_preloaded` when target model is not loaded
  - [ ] `error_if_other_model_loaded` on model mismatch
- [ ] Preserve backend/url/status/body detail quality in raised errors.

## Phase 7 - Tests

### Unit/adapter behavior

- [ ] Add tests for lifecycle payload parsing (legacy + new format).
- [ ] Add tests for unload policy behavior:
  - [ ] `immediate`
  - [ ] `after_idle` (timer scheduling/cancel/reschedule)
  - [ ] `never`
- [ ] Add tests for load/switch policies:
  - [ ] `ensure_loaded + auto_switch`
  - [ ] `require_preloaded`
  - [ ] `error_if_other_model_loaded`
- [ ] Add tests for chain deferral integration (`skip_unload=True`).
- [ ] Add tests for auth behavior on Textgen internal endpoints.

### Concurrency/race resilience

- [ ] **Risk #1 (URL keying):** Document that the lifecycle manager is keyed by normalized URL (shared server identity); add a test that two adapter instances targeting the same URL share one manager instance.
- [ ] Add tests simulating overlapping generation calls to same endpoint:
  - [ ] No unload while in-flight > 0
  - [ ] No load/unload thrash from interleaving calls

### Node output contract

- [ ] Add/update tests for `LLMLifecycleTextGenWebUI` output schema and OFF behavior.

## Phase 8 - Documentation and Release Notes

- [ ] **Risk #2 (process-local timer):** README + lifecycle node help/tooltip — `after_idle` is wall-clock since last adapter call in this ComfyUI process; restarts cancel the timer but do not unload Textgen; pair with Textgen auto-unload, explicit unload, or `immediate` for strict VRAM workflows.
- [ ] **Risk #6 (precedence):** README + generation node help — when both explicit `provider` and `meta.provider` apply, document **explicit provider wins, then meta** (and lifecycle in meta follows upstream widget updates on next run).
- [ ] Update `README.md` lifecycle section:
  - [ ] Explain Textgen policies and defaults
  - [ ] Add behavior table for `unload_policy`/`load_policy`/`switch_policy`
- [ ] Update `CHANGELOG.md` with migration-safe notes.
- [ ] Update `docs/resolution_tracker.md` if new architecture decisions or statuses change.
- [ ] Add `docs/lessons-learned.md` entry if implementation reveals non-obvious runtime behavior, design assumption breakage, or ComfyUI-specific workaround.

## Suggested execution order

- [ ] Implement Phase 1 and Phase 2 first (schema + parser), keep behavior parity.
- [ ] Implement Phase 3 and Phase 4 behind default-compatible paths.
- [ ] Add tests (Phase 7) before final docs/release updates.
- [ ] Finish with docs/changelog/tracker updates.

### Optional / proposal Phase 4 (utility nodes)

- [ ] **Risk #8:** If adding optional `Textgen Load Model` / `Textgen Unload Model` nodes (proposal Phase 4), gate on central manager from Phase 3 — nodes call the manager only, never duplicate adapter unload/load paths or bypass timer/`in_flight` rules.

### Cross-cutting backlog (optional / future)

- [ ] Optional: PromptServer “force refresh” endpoint + lifecycle UI control to resync after Textgen UI edits (mitigation if cache TTL feels sharp).
- [ ] Optional / future: `lifecycle_source_id` (or equivalent) to disambiguate two lifecycle nodes same URL — log-friendly policy source; not required for initial ship.

### Finalize before ship (open decisions from proposal)

- [ ] Decide and document: `idle_seconds = 0` when `after_idle` — disallow vs treat as immediate unload.
- [ ] Decide: timer persistence (process-local only vs any cross-restart semantics — proposal assumes process-local).
- [ ] Decide: lifecycle manager module scope (`oai_compat` only vs shared module).
- [ ] Decide: strict policies (`require_preloaded`, `error_if_other_model_loaded`) in Basic UI vs advanced toggle.

## Definition of done

- [ ] Existing workflows with old Textgen lifecycle payload keep working unchanged (including legacy-mapped **`immediate`** default at chain end, aligned with A-15/A-18).
- [ ] New lifecycle policies are selectable and enforced correctly.
- [ ] Chain-aware deferral still works exactly as expected.
- [ ] Default graphs ship **`unload_policy = immediate`**; users can opt into **`after_idle`** to reduce reload thrash during iteration.
- [ ] Strict deterministic users can disable implicit switching/loading.
