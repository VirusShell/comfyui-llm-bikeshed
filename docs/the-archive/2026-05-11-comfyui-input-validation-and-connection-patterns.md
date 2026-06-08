# ComfyUI Input Validation and Connection Patterns

- Date archived: 2026-05-11
- Archived by: Cursor agent session
- Scope: Single-connection validation strategies for `LLM_OPTIONS` + provider/backend compatibility in ComfyUI custom nodes

---

## Summary

ComfyUI supports strong connection safety through custom type strings and graph-level type validation, but `VALIDATE_INPUTS` does not receive runtime values from connected nodes. For semantic matching (for example, options payload backend vs detected provider backend), the reliable approach is runtime validation in node execution code, optionally combined with stricter custom types to prevent obvious miswiring at graph-edit time.

---

## Entries

### R-2026-05-11-001

- topic: `VALIDATE_INPUTS` receives constants, not connected runtime payloads
- captured_at: 2026-05-11
- source_posted_at: unknown (living docs page)
- source_url: https://docs.comfy.org/custom-nodes/backend/server_overview
- source_type: official_docs
- finding:
  - The docs state that `VALIDATE_INPUTS` runs before execution and only receives constant workflow inputs as values.
  - Inputs coming from other nodes are not available as runtime values in this method.
- implication_for_project:
  - We cannot depend on `VALIDATE_INPUTS` to inspect connected `LLM_OPTIONS` dict contents (such as backend tags).
- confidence: high

### R-2026-05-11-002

- topic: `input_types` in `VALIDATE_INPUTS` provides connected output type names
- captured_at: 2026-05-11
- source_posted_at: unknown (living docs page)
- source_url: https://docs.comfy.org/custom-nodes/backend/server_overview
- source_type: official_docs
- finding:
  - If `VALIDATE_INPUTS` includes an argument named `input_types`, ComfyUI passes a dictionary mapping connected input names to the upstream output type string.
  - This is type-level metadata, not the connected value payload.
- implication_for_project:
  - This can enforce type-family compatibility if we split options into distinct custom types, but cannot directly compare provider runtime backend fields.
- confidence: high

### R-2026-05-11-003

- topic: Type system blocks incompatible links in the editor
- captured_at: 2026-05-11
- source_posted_at: unknown (living docs page)
- source_url: https://docs.comfy.org/custom-nodes/backend/datatypes
- source_type: official_docs
- finding:
  - ComfyUI uses type strings in `INPUT_TYPES` and `RETURN_TYPES`.
  - Incompatible type links are prevented by the client graph editor.
- implication_for_project:
  - Splitting options outputs into backend-specific custom types is the most robust non-hacky way to prevent wrong connections while keeping a single options input socket as a typed union.
- confidence: high

### R-2026-05-11-004

- topic: JavaScript extension hooks can add editor-time behavior
- captured_at: 2026-05-11
- source_posted_at: unknown (living docs pages)
- source_url: https://docs.comfy.org/custom-nodes/js/javascript_hooks
- source_type: official_docs
- finding:
  - ComfyUI exposes extension hooks like `beforeRegisterNodeDef`, `nodeCreated`, `setup`, and graph access APIs.
  - These can be used to add custom warnings or guardrails in the editor experience.
- implication_for_project:
  - "Hacky but effective" UX guardrails are possible in JS (for example warning on suspect wiring), but they should not be the only enforcement path because server-side execution still needs authoritative validation.
- confidence: medium

### R-2026-05-11-005

- topic: Primitive-node behavior confirms `VALIDATE_INPUTS` runtime-value limitation
- captured_at: 2026-05-11
- source_posted_at: see issue timeline
- source_url: https://github.com/Comfy-Org/ComfyUI/issues/7888
- source_type: github_issue
- finding:
  - The issue discussion aligns with docs: primitive-connected values are not reliably available in `VALIDATE_INPUTS` as runtime payloads.
- implication_for_project:
  - Reinforces using execution-time validation for cross-input semantic checks.
- confidence: medium

### R-2026-05-11-006

- topic: Optional-input validation behavior is still evolving
- captured_at: 2026-05-11
- source_posted_at: see issue timeline
- source_url: https://github.com/comfyanonymous/ComfyUI/issues/8017
- source_type: github_issue
- finding:
  - There is active discussion about better optional input handling in `VALIDATE_INPUTS`.
- implication_for_project:
  - Avoid designs that rely on undocumented optional-input validation behavior; prefer explicit types plus runtime checks.
- confidence: medium

### R-2026-05-11-007

- topic: Local mirrored research corpus documents same constraints
- captured_at: 2026-05-11
- source_posted_at: local mirror entry says last fetched 2026-02-26
- source_url: https://docs.comfy.org/custom-nodes/backend/server_overview
- source_type: local_mirror
- finding:
  - Local mirror file `D:\ai\tmp\comfyui-custom-nodes-research\03-backend-properties.md` (Feb 2026 off-repo corpus; see `docs/research/external-comfyui-reference-corpus.md`) explicitly records:
    - `VALIDATE_INPUTS` gets constants, not node-connected values.
    - `input_types` can be used for type validation of connected inputs.
- implication_for_project:
  - Confirms our archive can safely cite both canonical docs URL and local mirror snapshots when preserving provenance. Future captures should prefer in-repo paths if the corpus is vendored (DOC-1).
- confidence: high

### R-2026-05-11-008

- topic: Community "advanced pack" evidence for this exact pattern remains partial
- captured_at: 2026-05-11
- source_posted_at: varies by repository
- source_url: https://github.com/rgthree/rgthree-comfy
- source_type: github_repo_reference
- finding:
  - During this pass, we found broad evidence of advanced graph tooling in major packs, but did not complete a deep code audit proving a canonical "single input plus semantic backend match" implementation pattern in a specific repo file.
- implication_for_project:
  - Treat "cool custom node does exactly this" as an open research task and capture exact code links before making architecture decisions based on ecosystem precedent.
- confidence: low

---

## Recommended Practical Pattern (Based on Captured Evidence)

1. Keep one `options` input on generation nodes.
2. Add backend identity metadata in each options node output payload.
3. In generation node execution, compare `options` metadata against resolved provider backend and fail fast with a clear error when mismatched.
4. Optionally split custom types per options backend to block obvious miswires at graph-edit time.
5. Optionally add JS editor warnings for better UX, but keep backend validation authoritative.

---

## Open Research Tasks to Archive Later

- Find concrete code references in well-known custom node repos that:
  - enforce cross-input semantic compatibility at runtime, or
  - use JS graph hooks to block/warn on suspect links.
- Record exact file URLs and commit SHAs per example.
- Add separate archive entries for each verified pattern.

