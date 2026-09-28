# Product direction & scope (proposal)

**Status:** **Historical / candidate source** (honesty scrub 2026-09-28). Not authoritative product and not the live queue ([`WORKLIST.md`](../../WORKLIST.md)). Captures stakeholder direction as of 2026-05, with a **2026-09-14** clarification that treated llama.cpp as an OAI Compatible path. It does not authorize implementation. The resolution tracker is also historical.

**Shipped since this note (v1.1.0):** the intended graph is **LLM Connection → LLM Generate (Advanced)**. **Q6** removed model-pick preload (do not read "load-on-select" below as current UX). **A-25** shipped one Connection **Manage VRAM** toggle (Textgen / LM Studio). Manage VRAM OFF does not embed a lifecycle. **Q5** shipped Properties `unload_on_interrupt` (default off). The Textgen lifecycle-manager rehaul did not ship.

**Reality check (2026-06-08):** Core v1 nodes are **shipped** (OAI/Textgen providers, lifecycle nodes, Basic/Advanced generation, per-provider options). Lifecycle **UX** remains under rethink below - existing lifecycle wiring is operational, not validated as the final product model.

## Textgen-first priority

Engineering and UX attention should favor **text-generation-webui (Textgen)** integration and shared generation/core features until that path feels solid. A 2026-05 pass tightened provider refresh latency (parallel backend probes, parallel Textgen list + model/info) and fixed OAI-compat UI state for **detected backend** and **loaded model** readouts; further lifecycle work remains deferred per below.

## Lifecycle: full rethink (do not assume current designs)

**Shipped instead (A-25, v1.1.0):** new graphs use one Connection **Manage VRAM** toggle. OFF does not embed a lifecycle. The policy manager in the rehaul did not ship. Legacy Lifecycle nodes stay registered.

Current **lifecycle code** (Textgen/LM Studio lifecycle nodes, adapter load/unload paths) and the **Textgen lifecycle overhaul** described in [`textgen-rehaul.md`](textgen-rehaul.md) were **not** treated as the long-term mental model when this section was written. They may be technically coherent yet still wrong for how people expect ComfyUI graphs to behave.

Expect a **full rethink** of lifecycle UX and architecture-not incremental polish on the existing proposal-before treating any lifecycle manager design as authoritative. The rehaul document may still **inform** a future design or may be **largely superseded** once the rethink lands; cross-links between these files stay explicit so readers do not merge them into one "approved spec" in their heads.

## Ollama: removed from this pack (shipped)

**Direction:** **Ollama** is not a supported backend in this node pack as of **v0.3.0** (2026-05-12). Other ComfyUI custom nodes cover native Ollama; this pack focuses on OAI-compat (LM Studio, Textgen, OpenAI, etc.). URL auto-detection may still label a host as `ollama` for the OAI provider indicator only.

**Execution:** See [`ollama-removal-plan.md`](ollama-removal-plan.md) (checklist completed) and `CHANGELOG.md` [0.3.0].

## llama.cpp: OAI Compatible first-class; dedicated node deferred

**In scope as of 2026-09-14 (wording below is historical):** llama.cpp servers that expose OpenAI-compatible HTTP (`/v1/chat/completions`, typically `/health` and `/v1/models`) were called a first-class path on **LLM Provider: OAI Compatible**, including load-on-select where the server supported it.

**Superseded (v1.1.0):** the first-class path is **LLM Connection** (host mode llama.cpp or Auto) into **LLM Generate (Advanced)**. Legacy **OAI Compatible** still loads old graphs. **Q6 removed load-on-select.** A dedicated llama-server node stays dead (D-4 closed). Presets still apply; wire them through Connection (see `presets/README.txt`).

**Still deferred:** a **dedicated** llama-server / llama.cpp provider or lifecycle node, and any pack-owned process manager for starting/stopping llama-server. Using **llama.cpp engines inside LM Studio or Textgen** remains a normal indirect path and is unchanged.

**Out of scope (unchanged):** vLLM-specific nodes; native Ollama return.

## Relationship to other proposals

- **[`textgen-rehaul.md`](textgen-rehaul.md)** - Detailed Textgen lifecycle ideas and an implementation checklist in [`textgen-rehaul-tasks.md`](textgen-rehaul-tasks.md). Per the stance in that proposal's *Status & scope* section, treat lifecycle-heavy portions as **skeptical / on hold** pending the rethink above; non-lifecycle items may still advance independently where they do not assume a specific lifecycle manager.
- **`docs/resolution_tracker.md`** - Minimal **Proposed / Tabled** rows point here so roadmap drift is visible next to historical decisions.
