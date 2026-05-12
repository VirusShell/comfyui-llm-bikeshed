# Textgen Lifecycle Rehaul Proposal

## Why this proposal exists

Current Textgen lifecycle behavior is technically valid but too narrow for real ComfyUI usage patterns. Today, lifecycle is effectively a binary switch:

- Enabled: ensure model loaded, run generation, unload at chain end
- Disabled: no load/unload management

This works for one policy ("VRAM-first, unload quickly") but does not cleanly support:

- Prompt iteration sessions (reuse a warm model briefly)
- Strict VRAM reclamation workflows (immediate unload)
- Long-lived text sessions (never unload unless manual)
- Deterministic pipelines where implicit model switching is undesirable

The goal is to keep current behavior available while introducing a policy-driven lifecycle model that supports all of the above without requiring separate node packs or custom branches.

## Current state summary

Textgen lifecycle is currently represented by a minimal dict from `LLM Lifecycle: Textgen`:

- `{"type": "text_gen_webui"}` when ON
- `{}` when OFF

Adapter behavior in `adapters/oai_compat.py`:

1. If lifecycle is active and type matches Textgen, call `GET /v1/internal/model/info`
2. If current model differs, call `POST /v1/internal/model/load`
3. Run `POST /v1/chat/completions`
4. If `skip_unload` is false (last generation node in chain), call `POST /v1/internal/model/unload`

Chain-awareness is derived from ComfyUI `PROMPT` reverse-indexing via hidden inputs (`prompt_graph`, `unique_id`), and this is correct for downstream unload deferral.

## Problems to solve

1. Single policy only
   - Lifecycle node expresses only ON/OFF, not intent.

2. Load/unload thrash during iteration
   - Immediate unload at chain end can force expensive reloads between frequent prompt tweaks.

3. Overhead from repeated state checks
   - `model/info` is queried per generation call even in stable sessions.

4. Hidden side effects
   - Generation can trigger heavy model switching implicitly, which may be surprising in production workflows.

5. Potential race conditions
   - Without a per-target runtime manager, overlapping requests can interleave load/unload operations.

## Design goals

1. Support multiple user behaviors with one coherent system
2. Preserve backward compatibility for existing workflows
3. Keep graph behavior readable and explicit
4. Retain ComfyUI chain-awareness (`skip_unload`) as a first-class signal
5. Avoid unnecessary API traffic and reduce VRAM thrash
6. Fail clearly when policy disallows implicit behavior

## Proposed lifecycle schema (Textgen)

Replace presence-only payload with explicit policy fields:

```python
{
    "type": "text_gen_webui",
    "enabled": True,
    "load_policy": "ensure_loaded",            # ensure_loaded | require_preloaded
    "unload_policy": "after_idle",             # immediate | after_idle | never
    "idle_seconds": 30,                        # used when unload_policy == after_idle
    "switch_policy": "auto_switch",            # auto_switch | error_if_other_model_loaded
}
```

Backward compatibility:

- Existing `{"type": "text_gen_webui"}` maps to defaults above
- Empty dict or missing lifecycle remains "disabled"

## Node changes

Update `LLM Lifecycle: Textgen` to expose policy controls:

- `manage_model_memory` (BOOLEAN, existing master switch)
- `unload_policy` (COMBO): `immediate`, `after_idle`, `never`
- `idle_seconds` (INT, min 0, visible/used for `after_idle`)
- `load_policy` (COMBO): `ensure_loaded`, `require_preloaded`
- `switch_policy` (COMBO): `auto_switch`, `error_if_other_model_loaded`

Behavioral intent:

- `manage_model_memory = OFF` returns `{}` (unchanged)
- ON returns full policy dict with defaults

UI notes:

- Keep at least one required widget to avoid empty-node rendering issues in ComfyUI
- Choose defaults that balance convenience and VRAM safety

## Adapter/runtime design

Introduce a lightweight in-process Textgen lifecycle manager in `oai_compat` adapter scope, keyed by target endpoint (e.g., backend + normalized URL).

Manager responsibilities:

1. Serialize lifecycle mutations per endpoint (lock)
2. Track in-flight request count
3. Track last known loaded model for optimization hints
4. Manage a cancellable unload timer for `after_idle`
5. Prevent unload while requests are active

### Request flow with policy

1. Resolve lifecycle policy (including compatibility defaults)
2. If lifecycle disabled, run chat request only
3. Before chat:
   - Read current model state (or cached state when valid)
   - Apply `load_policy` + `switch_policy`:
     - `ensure_loaded` + `auto_switch`: load target model when needed
     - `require_preloaded`: error if target model not already loaded
     - `error_if_other_model_loaded`: error on mismatch instead of switching
4. Run chat request
5. On completion:
   - If `skip_unload == True`: never unload now (chain continues)
   - Else apply `unload_policy`:
     - `immediate`: unload now
     - `after_idle`: schedule unload after `idle_seconds` unless new request arrives
     - `never`: do nothing

### Concurrency safeguards

- Acquire per-endpoint lock around load/switch/unload operations
- Maintain `in_flight` counter:
  - Increment before chat starts
  - Decrement in `finally`
- Timer callback checks `in_flight == 0` and no recent activity before unloading
- Cancel pending timer when a new request starts

## Interaction with ComfyUI chain introspection

No change to generation node graph logic:

- Keep hidden inputs and `has_downstream_gen_node(...)`
- Keep `skip_unload` signal passed to adapter

Interpretation update:

- `skip_unload` is a hard deferral signal for this call
- On chain end (`skip_unload=False`), lifecycle policy decides final unload behavior

This preserves existing chain semantics while adding broader memory policies.

## Error model and observability

### Error handling

- Use explicit exceptions for policy violations:
  - `require_preloaded` and model not loaded
  - `error_if_other_model_loaded` and mismatch detected
- Keep backend URL, status code, and response body in surfaced errors where possible

### Logging additions

At `info` level:

- Lifecycle policy chosen per request
- Whether unload was skipped due to chain
- Why unload was delayed, immediate, or suppressed
- Whether model switch happened or was blocked by policy

This reduces "mystery behavior" in ComfyUI console logs.

## Backward compatibility strategy

Phase in without breaking existing graphs:

1. Accept old lifecycle shape and map to defaults
2. Keep `manage_model_memory` OFF behavior unchanged (`{}`)
3. Keep provider and generation node connection contracts unchanged

Existing workflows should continue to execute without edits.

## Rollout plan

### Phase 1: Schema + node UI (non-breaking)

- Extend `LLM Lifecycle: Textgen` output schema
- Add adapter compatibility parser (old shape -> default policy)
- Keep current functional behavior under default policy

### Phase 2: Runtime manager + policies

- Add per-endpoint lifecycle manager (lock, in-flight, timer)
- Implement `after_idle`, `never`, and strict load/switch policies
- Ensure chain-aware deferral still takes precedence per call

### Phase 3: Diagnostics + docs

- Improve logs and error messages
- Update README lifecycle section with policy matrix and examples
- Document migration notes in CHANGELOG

### Phase 4 (optional): explicit utility nodes

- Consider separate `Textgen Load Model` / `Textgen Unload Model` utility nodes
- Useful for users who want deterministic orchestration with zero implicit lifecycle side effects

## Validation and test plan

Minimum required coverage:

1. Legacy lifecycle payload still works
2. `immediate` unload unloads only at chain end
3. `after_idle` unload cancels/reschedules correctly during repeated runs
4. `never` keeps model loaded across executions
5. `require_preloaded` errors when model is absent/mismatched
6. `error_if_other_model_loaded` blocks auto-switch
7. Concurrent calls do not race into unintended unload/load churn
8. Auth behavior still respects `admin_key`/`api_key` fallback for internal endpoints

Manual ComfyUI verification:

- Two-node generation chain with meta passthrough
- Rapid queue repeats to test idle timer behavior
- Switching models between runs with each switch policy

## Recommended default policy

Balanced defaults for most mixed workloads:

- `enabled = true`
- `load_policy = ensure_loaded`
- `unload_policy = after_idle`
- `idle_seconds = 30`
- `switch_policy = auto_switch`

Rationale:

- Retains convenience for first-run and model selection
- Greatly reduces load/unload thrash during prompt iteration
- Still reclaims VRAM quickly after activity pauses

## Open decisions to finalize before implementation

1. Should `idle_seconds=0` be allowed and interpreted as immediate unload?
2. Should `after_idle` timer be process-local only (simple) or persisted across reloads (likely unnecessary)?
3. Should lifecycle manager state be shared across adapters/modules or scoped to `OAICompatAdapter` only?
4. Should strict policies (`require_preloaded`, `error_if_other_model_loaded`) be exposed in Basic UX, or gated behind an advanced toggle?

## Success criteria

This rehaul is successful when:

1. Existing workflows continue working unchanged
2. Users can select memory behavior intentionally without code changes
3. Iterative prompt workflows show fewer expensive model reloads
4. VRAM-first workflows still unload aggressively when desired
5. Logs clearly explain lifecycle decisions during execution

---

## Risk review & mitigations

Concerns raised in design review (2026-05-11). Status values: **Open**, **Mitigated-by-design**, **Not-an-issue**, **Needs-implementation**, **Needs-documentation**.

| # | Concern | Legitimate? | Mitigation | Status |
|---|---------|-------------|------------|--------|
| 1 | Per-URL global lifecycle manager shares state across workflows hitting the same Textgen URL | Partial — but matches reality | Textgen is a single-process server with a single loaded model; URL identity *is* server identity. Keying the manager by normalized URL is intentional, not accidental coupling. Document the keying explicitly; add a test asserting two adapter instances pointed at the same URL share one manager. | Mitigated-by-design |
| 2 | `after_idle` is a process-local timer; user expectations vs "time since last adapter call"; ComfyUI/queue/server restart | Yes | Timer measures wall-clock since last adapter call in the current ComfyUI Python process. Restarting ComfyUI cancels the timer but does **not** unload Textgen — model stays in VRAM until something else evicts it. Document this semantics in the lifecycle node tooltip and README. Recommend pairing with Textgen's own auto-unload, an explicit Unload node, or `immediate` policy for strict VRAM workflows. | Needs-documentation |
| 3 | `threading.Timer` worker thread vs sync `FUNCTION`; lock/reentrancy with `requests`; ComfyUI execution threading model | Yes | **Confirmed:** ComfyUI processes prompts serially (single global execution queue — see Comfy-Org/ComfyUI issues #10072, #12082). Concurrent FUNCTION calls from different prompts cannot happen by default. The remaining race is the unload timer thread firing against a starting generation. Design: per-endpoint `threading.RLock` guards *only* state transitions (timer cancel/schedule, `in_flight` increment/decrement, load/switch decision). HTTP calls run outside the lock. Timer callback acquires lock, re-checks `in_flight == 0` and `last_activity` ≥ `idle_seconds` ago, then issues the unload HTTP call (without holding the lock during the network round-trip). | Needs-implementation |
| 4 | `model/info` caching is stale if user changes model in Textgen UI | Yes | Treat cached "currently loaded model" as a hint with a short TTL (5 s default, configurable). On cache miss/expiry, refresh via `GET /v1/internal/model/info` before issuing a switch. Invalidate cache on any 4xx/5xx response from generate or load endpoints — the server state is no longer trustworthy. Optional: surface a "stale cache detected" info log so users can correlate behavior with their UI actions. | Needs-implementation |
| 5 | `GENERATION_CLASS_TYPES` hardcoded set in `graph/introspection.py` — whitelist drift when new generation nodes are added | Yes — already bit us (see lessons-learned 2026-04-27, `LLMGenerateTest` omission) | Replace the hardcoded set with a single registry. Two viable patterns: (a) class-attribute marker (`IS_GENERATION_NODE = True`) and have `has_downstream_gen_node` look up `class_type` in `NODE_CLASS_MAPPINGS` to check the marker; (b) declare a small `GENERATION_NODE_CLASSES` list in `nodes/__init__.py` alongside `NODE_CLASS_MAPPINGS` and import-derive the names from it. Either removes the duplication and the registration ceremony. Add a CI/test assertion: every class in `NODE_CLASS_MAPPINGS` whose `RETURN_TYPES` contains `LLM_META` must be discoverable by `has_downstream_gen_node`. | Needs-implementation |
| 6 | Meta passthrough carries provider+lifecycle; policy changes "only when graph rewired" | Partial — mostly a UX/documentation concern | Widget value changes re-execute upstream nodes, so a policy edit on the upstream `LLM Lifecycle: Textgen` node propagates into meta on the next run — the "only when rewired" framing is incorrect. The real ambiguity is the `LLMGenerateAdvanced` precedence when both `meta.provider` and an explicit `provider` input are connected: current code (and this proposal) defines `explicit provider wins, then meta`. Document this precedence in the node help text and README. No code change needed beyond the documentation. | Mitigated-by-design |
| 7 | Recommended default `after_idle` 30 s conflicts with A-18 "explicit unload, VRAM-first" | Yes | A-18 commits Textgen to explicit unload-at-chain-end as the VRAM-first default. The original recommendation here (`after_idle = 30 s`) silently shifts that contract. **Revise default to `unload_policy = immediate`** to preserve A-18 semantics for existing workflows. Expose `after_idle` as a deliberate opt-in for iteration sessions, with a clear node-help hint that it trades VRAM for warmth. If a future product decision wants `after_idle` as the new default, update A-18 in `resolution_tracker.md` in the same change so the docs don't drift. | Open (product decision) |
| 8 | Optional Phase 4 explicit Load/Unload utility nodes risk double-unload / conflicting authority with central manager | Yes | Mandatory invariant: utility nodes call into the central manager — they never bypass it with direct adapter calls. Utility load: cancels any pending unload timer, sets `in_flight += 1` (held until matching Unload or chain end), marks lifecycle source = "explicit". Utility unload: cancels timer, decrements `in_flight`, marks "explicitly unloaded". A subsequent generation under `ensure_loaded` will re-check `model/info` and reload as normal. Gate Phase 4 behind the central manager landing in Phase 2; do not ship utility nodes that talk to the adapter directly. | Open (Phase 4 gate) |

### Cross-cutting follow-ups

- **Open decision #5 (new):** Should the manager expose a "force refresh" PromptServer endpoint (and a frontend button on the Lifecycle node) so users can resync after editing the Textgen UI? This is the cheapest mitigation for concern #4 if cache TTL feels too aggressive.
- **Open decision #6 (new):** Should `LLM Lifecycle: Textgen` carry a `lifecycle_source_id` field (random per-node-instance) so the manager can disambiguate two lifecycle nodes pointed at the same URL with different policies? Today the manager is URL-scoped; this would let policy decisions follow the most recently observed lifecycle dict per URL with a clear log line ("policy override from lifecycle node N").

### Tracker delta

- Concern #5 reinforces a known hazard from `docs/lessons-learned.md` (2026-04-27 entry). No new lessons-learned entry is added here because this section is prospective design review for an unbuilt feature, not a verified runtime finding.
- Concern #7 may require an explicit update to `docs/resolution_tracker.md` (A-18) if the team chooses to change the default away from `immediate`. Until that decision is made, A-18 remains the source of truth.
