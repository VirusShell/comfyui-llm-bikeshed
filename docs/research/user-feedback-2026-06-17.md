# User feedback triage — providers, URL refresh, cancel QA

**Date:** 2026-06-17  
**Scope:** Empirical UX issues and QA methodology corrections from operator session (ComfyUI v0.18.1 / v0.25.0). Code-read triage same day.

Write-time rules: [`provenance-and-reverification.md`](provenance-and-reverification.md). Template: [`research-note-template.md`](research-note-template.md).

---

## Summary — what we believe

- **Multi-provider URL bug (confirmed):** With **LLM Provider: OAI Compatible** and **LLM Provider: Textgen** on the same graph, editing the Textgen node's `url` may not refresh model list / status widgets until **Refresh Models** is clicked. Editing the OAI node's `url` can update immediately. Reproduced on ComfyUI frontend 1.39.19 and 1.45.15.
- **Cancel empirical (confirmed):** Textgen **v4.9** — ComfyUI Cancel stops inference immediately. LM Studio **v0.4.16** — Cancel does **not** stop inference (expected per pack docs); user wants future fix; no obvious mid-gen model eject errors.
- **Provider redundancy (UX, unresolved):** OAI Compatible vs Textgen provider nodes overlap when URL points at Textgen; lifecycle nodes only wire into OAI Compatible; Textgen provider embeds lifecycle toggle — ties to **D-2** lifecycle rethink.
- **Textgen model load (reported):** Provider cannot load a model when none is loaded in Textgen; dropdown lists models only. Adapter **does** implement load when `manage_model_memory` ON — failures likely config/auth/placeholder model (needs empirical trace).
- **`model_fallback`:** Not a visible widget when disconnected (`forceInput: True`); overrides COMBO when connected — **by design** (A-20).
- **`loaded_model_status`:** JS adds a `text` widget without `disabled` — **editable in UI** despite intent to be read-only.
- **Agent port probe (wrong):** Prior agent session probed default ports 5000/1234/8188/11434 on localhost; invalid for workflows with custom host URLs; Ollama probe out of pack scope (D-3).

---

## Verification

| Topic | Source | Access date | Status | Verified how |
|-------|--------|-------------|--------|--------------|
| URL refresh bug | User report + `js/model_dropdown.js` | 2026-06-17 | Confirmed empirical | `empirical` + `code read` |
| Textgen cancel stops inference | User report (Textgen v4.9) | 2026-06-17 | Confirmed | `empirical` |
| LM Studio cancel does not stop inference | User report (LM Studio v0.4.16) | 2026-06-17 | Confirmed (expected gap) | `empirical` |
| `model_fallback` override | `nodes/providers.py`, `tests/test_providers.py` | 2026-06-17 | Confirmed | `code read` |
| Textgen load path | `adapters/oai_compat.py` `_ensure_model_loaded` | 2026-06-17 | Shipped in code | `code read` |
| Default-port agent probe | `cancel-empirical-qa-handoff.md` § Agent probe | 2026-06-17 | **Invalid methodology** | `code read` + user correction |

---

## Applies to

- **Files:** `js/model_dropdown.js`, `nodes/providers.py`, `nodes/lifecycle.py`, `adapters/oai_compat.py`, `model_list.py`, `detection.py`
- **Tracker:** P-11, P-12, A-25, D-2, A-20; cancel rows in `cancel-interrupt-status.md`
- **Features:** Provider URL → model dropdown refresh; provider architecture; empirical cancel QA

---

## Falsifiers

- ComfyUI frontend change makes STRING `url` widget `callback` fire reliably for all provider nodes in multi-node graphs.
- Textgen load fails even with admin key configured, real model id, and `manage_model_memory` ON — would indicate adapter bug, not UX/config.

---

## Re-check triggers

- [ ] Changes to `js/model_dropdown.js` URL change handling
- [ ] ComfyUI frontend major version bump (STRING widget callback behavior)
- [ ] D-2 lifecycle redesign merges or removes redundant provider/lifecycle nodes
- [ ] New empirical cancel runs on LM Studio if stop API is scoped

---

## Multi-provider URL bug — code-read notes

`model_dropdown.js` attaches a debounced `urlWidget.callback` (500 ms) per provider node in `nodeCreated`. **Refresh Models** calls the same `runFetch` but reads `urlWidget.value` at click time.

**Leading hypotheses (not empirically isolated in devtools):**

1. STRING widget `callback` is not invoked reliably for every provider node when multiple provider nodes coexist (ComfyUI frontend 1.39.x–1.45.x); button path works because it does not depend on `callback`.
2. Callback receives stale `value` argument — `runFetch(value, …)` should use `urlWidget.value` (one-line fix candidate; not shipped this pass).
3. `nodeCreated` timing: if `url` widget is not in `node.widgets` when the hook runs, callback is never attached (less likely when Refresh reads correct URL from same closure).

**Not root cause:** Backend fingerprinting or wrong endpoint — Refresh fixes UI with same endpoint.

---

## Provider architecture (today)

| Node | Role |
|------|------|
| **LLM Provider: OAI Compatible** | Fingerprinting via `detect_backend`; model list via `POST /llm-bikeshed/models/oai-compat`; optional `lifecycle` input (LM Studio or Textgen lifecycle nodes). |
| **LLM Provider: Textgen** | Fixed `text_gen_webui` backend; `POST /llm-bikeshed/models/textgen` (no fingerprint); `manage_model_memory` embeds Textgen lifecycle (same as **LLM Lifecycle: Textgen** ON). |
| **LLM Lifecycle: LM Studio** | Connects only to OAI Compatible `lifecycle` input when detected backend is LM Studio. |
| **LLM Lifecycle: Textgen** | Connects only to OAI Compatible `lifecycle` input; **redundant** with Textgen provider's built-in toggle for new graphs. |

Product direction: consolidate under **D-2** rethink — see [`product-direction-and-scope.md`](../proposals/product-direction-and-scope.md).

---

## Correct backend reachability check (agents / CI)

Do **not** infer workflow backend state from default localhost ports.

| Approach | When |
|----------|------|
| Read `url` widget values from the workflow under test | Human or agent preparing QA |
| `POST /llm-bikeshed/models/oai-compat` or `/models/textgen` with `{"url": "<configured base>"}` | Pack-aware probe from ComfyUI host |
| `POST /llm-bikeshed/detect` with configured URL | Backend label only |
| TCP probe to `:5000` / `:1234` | Only if workflow still uses defaults |

**Do not probe Ollama `:11434`** — native Ollama removed from pack (D-3).
