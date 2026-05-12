# Textgen Rehaul Implementation Checklist

This checklist is intentionally separated from active project specs/docs.  
It is scoped to implementing `docs/proposals/textgen-rehaul.md`.

## Phase 1 - Schema and Node Contract (non-breaking)

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

- [ ] Add tests simulating overlapping generation calls to same endpoint:
  - [ ] No unload while in-flight > 0
  - [ ] No load/unload thrash from interleaving calls

### Node output contract

- [ ] Add/update tests for `LLMLifecycleTextGenWebUI` output schema and OFF behavior.

## Phase 8 - Documentation and Release Notes

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

## Definition of done

- [ ] Existing workflows with old Textgen lifecycle payload keep working unchanged.
- [ ] New lifecycle policies are selectable and enforced correctly.
- [ ] Chain-aware deferral still works exactly as expected.
- [ ] Iterative runs can avoid reload thrash via `after_idle`.
- [ ] VRAM-first users still get immediate unload behavior.
- [ ] Strict deterministic users can disable implicit switching/loading.
