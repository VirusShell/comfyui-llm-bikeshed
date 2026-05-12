# Product direction & scope (proposal)

**Status:** Living document — captures stakeholder direction as of 2026-05. It does **not** by itself change shipped code or supersede every row in `docs/resolution_tracker.md`; reconciling older “Decided” rows with this direction is a separate documentation pass when implementation catches up.

## Textgen-first priority

Engineering and UX attention should favor **text-generation-webui (Textgen)** integration and shared generation/core features until that path feels solid. Other backends remain in scope where they already exist, but **expanding** surface area (new lifecycle policies, new provider-specific features) should default to deferral unless it directly supports Textgen or shared adapters.

## Lifecycle: full rethink (do not assume current designs)

Current **lifecycle code** (Textgen/LM Studio lifecycle nodes, adapter load/unload paths) and the **Textgen lifecycle overhaul** described in [`textgen-rehaul.md`](textgen-rehaul.md) are **not** treated as validated as the long-term mental model for users. They may be technically coherent yet still wrong for how people expect ComfyUI graphs to behave.

Expect a **full rethink** of lifecycle UX and architecture—not incremental polish on the existing proposal—before treating any lifecycle manager design as authoritative. The rehaul document may still **inform** a future design or may be **largely superseded** once the rethink lands; cross-links between these files stay explicit so readers do not merge them into one “approved spec” in their heads.

## Ollama: planned removal from this pack

**Direction:** Remove **Ollama** as a supported backend from this node pack going forward. Other ComfyUI custom nodes already cover Ollama well; dropping it here reduces maintenance and scope.

**This repository stage:** **Documentation and tracker only** for this change unless a separate task explicitly deletes code. A follow-up implementation task should remove the Ollama native adapter, Ollama-specific nodes, and related config/docs references when execution is scheduled. Until then, Ollama may still appear in code and older docs—treat that as **legacy**, not endorsement.

## llama.cpp: explicit deferral

**Dedicated** llama.cpp server integration (or similar first-class support) stays **deferred** until Textgen and core generation workflows are in good shape. Using **llama.cpp engines inside LM Studio or Textgen** remains a normal indirect path and is unchanged by this deferral statement.

## Relationship to other proposals

- **[`textgen-rehaul.md`](textgen-rehaul.md)** — Detailed Textgen lifecycle ideas and an implementation checklist in [`textgen-rehaul-tasks.md`](textgen-rehaul-tasks.md). Per the stance in that proposal’s *Status & scope* section, treat lifecycle-heavy portions as **skeptical / on hold** pending the rethink above; non-lifecycle items may still advance independently where they do not assume a specific lifecycle manager.
- **`docs/resolution_tracker.md`** — Minimal **Proposed / Tabled** rows point here so roadmap drift is visible next to historical decisions.
