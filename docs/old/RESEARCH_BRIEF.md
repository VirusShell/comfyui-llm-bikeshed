# Research Brief: ComfyUI Custom Node Development Reference

## Objective

Create a comprehensive, practical reference document for ComfyUI custom node
development. This document will serve as the foundational knowledge base for
the `comfyui-llm-bikeshed` project and should be thorough enough to minimize
repeated lookups during implementation.

This is a **research-first** task. The goal is to understand how ComfyUI
actually works before making any design or implementation decisions. Do not
frame findings around our specific project — frame them as general ComfyUI
node development knowledge that happens to be useful for any node pack.

## Primary Source

**ComfyUI Official Documentation:** https://docs.comfy.org

Start here. This should be the backbone of the reference. Crawl the full
custom node development section systematically:

- https://docs.comfy.org/custom-nodes/overview
- https://docs.comfy.org/custom-nodes/walkthrough
- https://docs.comfy.org/custom-nodes/backend/server_overview (Properties)
- https://docs.comfy.org/custom-nodes/backend/more_on_inputs
- https://docs.comfy.org/custom-nodes/backend/datatypes
- https://docs.comfy.org/custom-nodes/backend/tensors
- https://docs.comfy.org/custom-nodes/backend/lifecycle
- https://docs.comfy.org/custom-nodes/backend/lazy_evaluation
- https://docs.comfy.org/custom-nodes/backend/node_expansion
- https://docs.comfy.org/custom-nodes/backend/data_lists
- https://docs.comfy.org/custom-nodes/backend/annotated_examples
- https://docs.comfy.org/custom-nodes/js/javascript_objects_and_hijacking
- https://docs.comfy.org/custom-nodes/help_page
- https://docs.comfy.org/custom-nodes/backend/manager (Publishing)
- https://docs.comfy.org/registry/specifications
- https://docs.comfy.org/registry/cicd
- https://docs.comfy.org/development/core-concepts/nodes
- https://docs.comfy.org/development/core-concepts/links
- https://docs.comfy.org/development/core-concepts/dependencies

Not every page will be equally relevant. Use judgment on depth, but err on the
side of including more rather than less. If a page covers something we might
need later, capture it.

## Secondary Sources

**Developer community posts and articles.** Look for practical insights from
people who've actually built and maintained custom nodes. These fill gaps the
docs don't cover — gotchas, edge cases, undocumented behavior, best practices
learned the hard way.

Good places to look:
- GitHub discussions/issues on popular node packs (comfyui-ollama, WAS Node
  Suite, ComfyUI-Impact-Pack, ComfyUI-Custom-Scripts)
- Reddit r/comfyui — dev-focused posts about node development
- DEV Community / Medium articles on ComfyUI node development
- ComfyUI Discord (if searchable) — developer channels
- The ComfyUI source code itself (comfyanonymous/ComfyUI on GitHub) for
  understanding internal behavior when docs are insufficient

**Critical rule for secondary sources:** Cross-reference dates on everything.
A post from 2023 may describe patterns or behaviors that have since changed.
If a community source contradicts official docs, flag the discrepancy rather
than assuming either is correct. Prefer recent sources (2025+) where possible.

## What the Reference Document Should Cover

### 1. Node Execution Lifecycle
- How ComfyUI discovers and loads custom nodes on startup
- The order of operations: registration → graph resolution → execution
- Threading model: what thread(s) do node FUNCTION methods run on?
- Caching: how does IS_CHANGED work? When does ComfyUI skip re-execution?
- What happens when a node's FUNCTION raises an exception?
  - Does the workflow halt?
  - What does the user see?
  - Is there any cleanup or rollback?
- What happens when a node returns None or an unexpected type?
- OUTPUT_NODE behavior: what makes a node an "output" and why does it matter?

### 2. Input System (Complete)
- Required vs optional vs hidden inputs — full behavior differences
- Every widget type: STRING, INT, FLOAT, BOOLEAN, COMBO (dropdown)
  - All configuration options for each (default, min, max, step, multiline,
    placeholder, forceInput, defaultInput, display, dynamicPrompts, etc.)
  - How each renders in the UI
  - How each serializes in workflow JSON (this matters for API key security)
- Custom datatypes: how to define, how connections are typed/enforced
- forceInput vs defaultInput — exact behavioral difference
- Wildcard inputs ("*") — when to use, how VALIDATE_INPUTS interacts
- Dynamic inputs via ContainsAnyDict — use cases and limitations
- How optional inputs work in the function signature (default values, **kwargs)

### 3. Output System
- RETURN_TYPES and RETURN_NAMES
- Single vs multiple outputs
- How output data flows to connected nodes
- **Batch/list behavior**: if a node outputs multiple items (e.g., processing
  a batch of images and producing a string per image), how does ComfyUI handle
  this downstream? Is there a native list output type? How do downstream nodes
  receive list vs single outputs? How does this interact with the batch
  dimension of IMAGE tensors?
- OUTPUT_NODE = True behavior and implications

### 4. Error Handling & User Feedback
- What mechanisms exist for a custom node to communicate errors to the user?
- Exception handling: what does ComfyUI do when a node raises an exception?
  - Does it halt the entire workflow or just that branch?
  - What UI feedback does the user see? (red outline, notification, modal, etc.)
- Logging: how to write to ComfyUI's console output
- Are there APIs for:
  - Toast/notification messages in the UI?
  - Modal dialogs?
  - Node-level status text or indicators?
  - Progress reporting during long operations?
- How do built-in nodes and popular custom nodes handle error states?
- VALIDATE_INPUTS: when does it run, what can it return, how does validation
  failure present to the user?

### 5. Image/Tensor Handling
- IMAGE type: exact tensor format, shape, dtype, value range
- MASK type: same details
- LATENT type: same details
- Batch dimension: always present? How to handle single vs multi-image?
- Conversion patterns: tensor ↔ PIL ↔ numpy ↔ base64
- Common pitfalls (squeezed tensors, wrong dtype, channel order)
- How IMAGE batches flow through workflows — does ComfyUI auto-iterate?

### 6. Frontend JavaScript
- Extension registration: app.registerExtension() and available hooks
- nodeCreated, beforeRegisterNodeDef, getCustomWidgets — what each does
- How to add/modify widgets dynamically
- How to communicate between frontend JS and backend Python
  - Custom API endpoints (routes)
  - Message passing
- Dynamic dropdown population pattern (fetch model list, update COMBO widget)
- Current best practices vs deprecated patterns (monkey-patching, etc.)
- WEB_DIRECTORY: both "./web" and "./js" conventions — which is current?
- What JS APIs are stable vs fragile across ComfyUI versions?

### 7. Custom API Endpoints (Routes)
- How to register custom HTTP endpoints from a node pack
- The server routes system — how comfyui-ollama and others add endpoints
- Authentication/security considerations for custom endpoints
- How frontend JS calls these endpoints

### 8. Configuration & Secrets
- How do existing node packs handle configuration files?
- How does workflow JSON serialization work?
  - What widget values get saved?
  - How to ensure sensitive data (API keys) is NOT serialized
  - forceInput and other mechanisms to prevent widget serialization
- Environment variable access from within nodes
- Config file location conventions in the ecosystem

### 9. Publishing & Distribution
- ComfyUI Registry (modern path): pyproject.toml requirements, [tool.comfy]
  section, GitHub Action publishing
- ComfyUI Manager (legacy path): custom-node-list.json PR process
- Lifecycle scripts: install.py, uninstall.py, disable.py, enable.py
- requirements.txt best practices (permissive versioning)
- What makes a node pack "well-behaved" in the ecosystem?

### 10. V3 Node Specification (Awareness)
- Current status: what's implemented vs proposed vs theoretical?
- Key differences from V1
- What V1 patterns should be avoided now to ease future V3 migration?
- Is V1 expected to remain supported alongside V3? For how long?
- Any official guidance on V1 → V3 migration path?

### 11. Patterns from the Ecosystem
- Common architectural patterns in well-regarded node packs
- The "connectivity → options → generate" decomposition (comfyui-ollama)
- Meta/context passthrough patterns for node chaining
- How node packs organize categories in the menu
- Naming conventions for nodes, types, and display names
- How popular packs handle versioning (V1 → V2 node transitions)

## What to Flag

As you compile the reference, explicitly flag:

- **Ambiguities**: where the docs are unclear or could be interpreted
  multiple ways
- **Contradictions**: where different doc pages say different things, or
  where community sources contradict official docs
- **Gaps**: topics the docs don't cover at all that seem important
- **Version sensitivity**: behaviors that have changed between ComfyUI
  versions or are expected to change
- **Undocumented behavior**: things that work in practice but aren't
  officially documented (note these as potentially fragile)

## Format

Organize as a single markdown reference document. Use clear headings and keep
it scannable. Include code examples where they clarify behavior. Cite sources
(URL + date accessed) so we can verify and update later.

The tone should be practical and definitive: "ComfyUI does X when Y happens"
not "it appears that ComfyUI might do X." Where behavior is uncertain, say so
explicitly rather than hedging with vague language.

## What This Is NOT

- Not a tutorial (we're not learning ComfyUI from scratch)
- Not project-specific design (don't map findings to our node pack)
- Not implementation code (no skeleton files or boilerplate)
- Not exhaustive API documentation (focus on what matters for node development)

The goal is a reference we can hand to any developer working on this project
and say "read this first, it covers what you need to know about building
ComfyUI nodes." If questions come up during implementation that this document
should have answered, that's a gap worth noting.
