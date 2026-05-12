# Textgen Lifecycle Rehaul Proposal

## Status & scope

**Research authority:** Implementation and future lifecycle work **must not contradict** findings in [`docs/research/textgen-lifecycle-verified.md`](../research/textgen-lifecycle-verified.md) without updating that research file with new upstream sources (routes, auth split, response shapes).

**Design stance:** Lifecycle content in this document—the proposed policy schema, runtime manager, rollout phases, and related adapter behavior—is **not** validated as the correct long-term product design. It can conflict with common mental models for how model memory should behave in ComfyUI graphs. A **full rethink** of lifecycle UX and architecture is expected before locking anything in; see [`product-direction-and-scope.md`](product-direction-and-scope.md).

Until that rethink, treat implementation work on a Textgen lifecycle **manager** and policy-driven schema as **on hold** or **experimental**—useful as exploration, not as committed roadmap.

**Research-backed slice (2026-05-12):** Verified Textgen HTTP/auth behavior against upstream `oobabooga/textgen` is summarized in [`docs/research/textgen-lifecycle-verified.md`](../research/textgen-lifecycle-verified.md). Implemented in code: correct **API vs admin Bearer** usage for `GET /v1/internal/model/info` vs load/unload; normalization of idle `model_name`; model refresh API + UI for **detected backend** and **loaded model** on the OAI-compat provider. **Still deferred:** policy manager, idle timers, traffic reduction for repeated `model/info`, and any change to the binary lifecycle node beyond clarifications grounded in further product decisions.

Sections that are only **tangentially** tied to lifecycle (for example diagnostics, optional utility nodes, or traffic-reduction ideas) still carry **uncertainty** wherever they assume a particular lifecycle core; they may survive a redesign in another form, or they may need revision once the lifecycle story is clearer.

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
2. Preserve **data and graph** compatibility where practical; breaking misleading UX is acceptable when documented (migration notes, CHANGELOG)
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
    "unload_policy": "immediate",              # immediate | after_idle | never (VRAM-first default)
    "idle_seconds": 30,                        # used when unload_policy == after_idle
    "switch_policy": "auto_switch",            # auto_switch | error_if_other_model_loaded
}
```

Backward compatibility:

- Existing `{"type": "text_gen_webui"}` maps to the same defaults as the recommended block below (`unload_policy = immediate`, same other fields)
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

- Lifecycle nodes should **communicate purpose** clearly: node titles, tooltips/help text, and (where useful) README copy so operators know what the node does without inferring from widget chrome alone.
- ComfyUI legitimately supports purpose-built nodes with **no visible widgets** when the role is obvious; an empty-looking node is a **product clarity** problem, not a platform defect to paper over with a dummy control. **Avoid** adding a BOOLEAN or other widget solely to force a “body” on the card—prefer real labels and documentation instead.
- When a BOOLEAN (or similar) **is** the real product control—for example a master enable—name and document it as that control, not as a rendering workaround inherited from older lifecycle UX.
- Choose defaults that prioritize VRAM reclamation; expose `after_idle` as an explicit iteration-session opt-in

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
- Keep legacy payload mapping aligned with recommended defaults (`immediate` unload at chain end, consistent with A-15 explicit unload)

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

VRAM-first defaults for new graphs and for legacy `{"type": "text_gen_webui"}` mapping (same values):

- `enabled = true`
- `load_policy = ensure_loaded`
- `unload_policy = immediate`
- `idle_seconds = 30` (applies when `unload_policy == after_idle`; ignored for `immediate` / `never`)
- `switch_policy = auto_switch`

Rationale:

- Matches A-15 / A-18 intent: explicit unload at chain end by default so diffusion can reclaim VRAM immediately after the last generation node
- Users doing prompt iteration opt into `after_idle` (and tune `idle_seconds`) to trade VRAM hold time for fewer reloads
- Retains convenience for first-run and model selection via `ensure_loaded` + `auto_switch`

## Open decisions to finalize before implementation

Stakeholder / review input (2026-05-12) — fold into design before treating lifecycle manager work as committed:

1. **`idle_seconds`:** Clarify semantics for `0` vs `-1` (if ever allowed): e.g. is `0` “immediate unload after idle check” or invalid? Prefer documenting one convention and rejecting ambiguous values in the node validator.
2. **`after_idle` scope:** Spell out that unload timers are **process-local** (this ComfyUI Python process): wall-clock since the last adapter call here; ComfyUI or queue restarts cancel the timer but **do not** unload Textgen — VRAM may still hold the model until Textgen policy, an explicit unload, or another client acts.
3. **Manager scope vs detection:** Per-endpoint manager keying (normalized URL + backend id) should stay aligned with how the pack already fingerprints Textgen vs generic OAI at the same port; document that URL identity is server identity for a single loaded model, and that two graphs with different lifecycle policies on the same URL remain a product tension (see risk table #1 / follow-up on `lifecycle_source_id`).
4. **`require_preloaded`:** Do **not** treat as the default happy path — it is a strict / automation mode. Prefer documenting it as an edge policy or anti-pattern for casual graphs unless the UX makes the failure mode obvious.
5. **`error_if_other_model_loaded`:** Critique stands — easy to misconfigure vs `auto_switch`; if it stays in the schema, tooltips and errors must say *which* model was loaded vs *which* was requested, and when to use `auto_switch` instead.
6. **Basic vs Advanced generation nodes:** Any lifecycle policy surface that is easy to get wrong (`require_preloaded`, strict switch policies, idle tuning) should default to **Advanced** or behind an explicit “expert” expander; Basic should keep VRAM-first defaults and minimal knobs.

## Success criteria

This rehaul is successful when:

1. **Honest evolution:** “No regressions” is a **migration and communication** goal (CHANGELOG, porting notes), not a veto on replacing UX that was wrong or misleading. Prefer one-time user-visible fixes over preserving broken indicators “because it shipped.”
2. **Intent without code forks:** Users can steer memory behavior via **node controls and documented config**, not by editing the adapter or maintaining private branches — including clear defaults and opt-ins (`after_idle`, `never`, etc.).
3. **Chain + meta stay legible:** `skip_unload`, meta passthrough, and lifecycle policy interact in ways we **document with explicit precedence** (what wins when policy and chain hints disagree). Success is not “behaves like stock ComfyUI” for every knob; it is “operators can predict the next run from the graph + docs.”
4. **VRAM posture is explicit:** Aggressive reclaim vs “hold warm model” is a **documented trade-off** (defaults, tooltips, logs), not something inferred only from timing side effects.
5. **Observability:** Lifecycle decisions are explained in logs, and **log verbosity is configurable** (see commented `logging` proposal in [`config.example.yaml`](../../config.example.yaml); wiring TBD — goal is debuggable sessions without recompiling).

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
| 7 | Prior doc default `after_idle` 30 s vs A-18 / VRAM-first explicit unload | Yes | **Resolved in this proposal:** shipped defaults use `unload_policy = immediate` for new graphs and legacy payload mapping; `after_idle` is an explicit opt-in (node help should say it trades VRAM for warmth). Aligns with A-15 explicit unload and A-18 text-gen-webui explicit-unload posture; no tracker change unless product later redefaults to `after_idle`. | Mitigated-by-design |
| 8 | Optional Phase 4 explicit Load/Unload utility nodes risk double-unload / conflicting authority with central manager | Yes | Mandatory invariant: utility nodes call into the central manager — they never bypass it with direct adapter calls. Utility load: cancels any pending unload timer, sets `in_flight += 1` (held until matching Unload or chain end), marks lifecycle source = "explicit". Utility unload: cancels timer, decrements `in_flight`, marks "explicitly unloaded". A subsequent generation under `ensure_loaded` will re-check `model/info` and reload as normal. Gate Phase 4 behind the central manager landing in Phase 2; do not ship utility nodes that talk to the adapter directly. | Open (Phase 4 gate) |

### Cross-cutting follow-ups

- **Open decision #5 (new):** Should the manager expose a "force refresh" PromptServer endpoint (and a frontend button on the Lifecycle node) so users can resync after editing the Textgen UI? This is the cheapest mitigation for concern #4 if cache TTL feels too aggressive.
- **Open decision #6 (new):** Should `LLM Lifecycle: Textgen` carry a `lifecycle_source_id` field (random per-node-instance) so the manager can disambiguate two lifecycle nodes pointed at the same URL with different policies? Today the manager is URL-scoped; this would let policy decisions follow the most recently observed lifecycle dict per URL with a clear log line ("policy override from lifecycle node N").

### Tracker delta

- Concern #5 reinforces a known hazard from `docs/lessons-learned.md` (2026-04-27 entry). No new lessons-learned entry is added here because this section is prospective design review for an unbuilt feature, not a verified runtime finding.
- Concern #7: proposal defaults now match A-15/A-18 (`immediate` at chain end). Update `docs/resolution_tracker.md` (A-18) only if future product changes the shipped default away from `immediate`.
