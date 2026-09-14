# Product direction & scope (proposal)

**Status:** Living document - captures stakeholder direction as of 2026-05, with a **2026-09-14** clarification on llama.cpp via OAI Compatible. It does **not** by itself change shipped code or supersede every row in `docs/resolution_tracker.md`; reconciling older "Decided" rows with this direction is a separate documentation pass when implementation catches up.

**Reality check (2026-06-08):** Core v1 nodes are **shipped** (OAI/Textgen providers, lifecycle nodes, Basic/Advanced generation, per-provider options). Lifecycle **UX** remains under rethink below - existing lifecycle wiring is operational, not validated as the final product model.

## Textgen-first priority

Engineering and UX attention should favor **text-generation-webui (Textgen)** integration and shared generation/core features until that path feels solid. A 2026-05 pass tightened provider refresh latency (parallel backend probes, parallel Textgen list + model/info) and fixed OAI-compat UI state for **detected backend** and **loaded model** readouts; further lifecycle work remains deferred per below.

## Lifecycle: full rethink (do not assume current designs)

Current **lifecycle code** (Textgen/LM Studio lifecycle nodes, adapter load/unload paths) and the **Textgen lifecycle overhaul** described in [`textgen-rehaul.md`](textgen-rehaul.md) are **not** treated as validated as the long-term mental model for users. They may be technically coherent yet still wrong for how people expect ComfyUI graphs to behave.

Expect a **full rethink** of lifecycle UX and architecture-not incremental polish on the existing proposal-before treating any lifecycle manager design as authoritative. The rehaul document may still **inform** a future design or may be **largely superseded** once the rethink lands; cross-links between these files stay explicit so readers do not merge them into one "approved spec" in their heads.

## Ollama: removed from this pack (shipped)

**Direction:** **Ollama** is not a supported backend in this node pack as of **v0.3.0** (2026-05-12). Other ComfyUI custom nodes cover native Ollama; this pack focuses on OAI-compat (LM Studio, Textgen, OpenAI, etc.). URL auto-detection may still label a host as `ollama` for the OAI provider indicator only.

**Execution:** See [`ollama-removal-plan.md`](ollama-removal-plan.md) (checklist completed) and `CHANGELOG.md` [0.3.0].

## llama.cpp: OAI Compatible first-class; dedicated node deferred

**In scope now (2026-09-14):** llama.cpp servers that expose OpenAI-compatible HTTP (`/v1/chat/completions`, typically `/health` and `/v1/models`) are a **first-class path on LLM Provider: OAI Compatible**. Detection labels, docs, UX (model list, loaded-model status, load-on-select where the server supports it), allowlists, and presets for that path are in-scope and should not be treated as "deferred."

**Still deferred:** a **dedicated** llama-server / llama.cpp provider or lifecycle node, and any pack-owned process manager for starting/stopping llama-server. Using **llama.cpp engines inside LM Studio or Textgen** remains a normal indirect path and is unchanged.

**Out of scope (unchanged):** vLLM-specific nodes; native Ollama return.

## Relationship to other proposals

- **[`textgen-rehaul.md`](textgen-rehaul.md)** - Detailed Textgen lifecycle ideas and an implementation checklist in [`textgen-rehaul-tasks.md`](textgen-rehaul-tasks.md). Per the stance in that proposal's *Status & scope* section, treat lifecycle-heavy portions as **skeptical / on hold** pending the rethink above; non-lifecycle items may still advance independently where they do not assume a specific lifecycle manager.
- **`docs/resolution_tracker.md`** - Minimal **Proposed / Tabled** rows point here so roadmap drift is visible next to historical decisions.
