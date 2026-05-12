# Ollama removal — execution plan

**Status:** Executed 2026-05-12 (code + docs). Aligns with product direction ([`product-direction-and-scope.md`](product-direction-and-scope.md) § Ollama) and tracker **D-3** ([`resolution_tracker.md`](../resolution_tracker.md)).

## 1. Goal / non-goals

**Goal (D-3):** Remove **Ollama as a first-class backend** from this pack: no Ollama-native adapter, no Ollama provider/options nodes, no Ollama-only PromptServer routes or JS wiring, no `providers.ollama` surface in shipped defaults—so maintenance and scope stay on Textgen, LM Studio, OAI-compat, and OpenAI.

**Non-goals:**

- Replacing ecosystem Ollama support (other Comfy packs remain the right place for native Ollama UX).
- Removing **URL/backend auto-detection** for the **OAI Compatible** provider solely because the probe can return `ollama` (see § Inventory — `detection.py`).
- Dedicated llama.cpp server work (still deferred per direction doc).

## 2. Inventory (repo grep / read, 2026-05-12)

| Area | Files / symbols | Action when executing removal |
|------|-----------------|--------------------------------|
| Registration | `__init__.py` — imports `LLMProviderOllama`, `LLMOptionsOllamaCore`, `LLMOptionsOllamaExtra`; `NODE_CLASS_MAPPINGS` / `NODE_DISPLAY_NAME_MAPPINGS` entries | Drop imports and mapping keys |
| Provider node | `nodes/providers.py` — `LLMProviderOllama` class and module docstring | Remove class; tighten docstring to OAI-only providers |
| Options nodes | `nodes/options_ollama.py` — `LLMOptionsOllamaCore`, `LLMOptionsOllamaExtra` | Delete file or strip classes after last import removed |
| Adapter | `adapters/ollama.py` — `OllamaAdapter` | Delete file |
| Adapter registry | `adapters/__init__.py` — `from .ollama import OllamaAdapter`, `"ollama_native"` entry in registry | Remove import and dict entry; ensure `get_adapter` callers have no dead `adapter` strings |
| Generation | `nodes/generation.py` — uses `get_adapter` generically | Audit for `backend == "ollama"` / `ollama_native` branches (none as of inventory); keep generic path |
| Model list | `model_list.py` — `_fetch_models_ollama` (`GET /api/tags`) | Remove if only used by Ollama endpoint; else fold into tests only |
| HTTP routes | `server/endpoints.py` — `POST /llm-bikeshed/models/ollama`, import of `_fetch_models_ollama` | Remove route and import |
| Frontend | `js/model_dropdown.js` — `PROVIDER_CONFIG.LLMProviderOllama`, `BACKEND_LABELS.ollama` | Remove provider config entry; **keep** `BACKEND_LABELS.ollama` if OAI-compat still surfaces detected backend (see below) |
| Auto-detection | `detection.py` — `BACKEND_OLLAMA`, probe `GET /api/version` early in order | **Decision:** **Keep** Ollama classification for **OAI Compatible** URLs. Users may point the same host/port shapes at servers this pack does not own; removing the probe would mis-label logs/UI. This pack only removes **Ollama-specific nodes** and the **native** adapter—not the fact that a URL can behave like Ollama. If later product choice is “OAI node only talks to `/v1/*` servers,” revisit and possibly drop probe or map Ollama → `generic`. |
| Config | `config.example.yaml` — `providers.ollama` block | Remove block; document in CHANGELOG for users merging old `config.yaml` |
| Config code | `config/__init__.py`, `config/merge.py` | No Ollama-specific keys today beyond YAML shape; verify no `get("ollama")` assumptions outside removed nodes |
| Docs | `README.md`, `CHANGELOG.md` — Ollama feature lists | Rewrite counts, tables, and backend bullets |
| Agent / design | `CLAUDE.md` — overview table lists Ollama; adapter section mentions Ollama Native | Update supported-backend table and adapter list to match post-removal reality |
| Tracker | `docs/resolution_tracker.md` — **A-1**, **A-3**, **A-15**, **A-16**, **A-18**, **S-2**, **S-4**, **AA-1**, **AA-3**, **API-4**, **P-2** (and any other row whose Notes still assume in-pack Ollama nodes) | Phase C: set **D-3** to **Decided** when code ships; mark conflicting rows **Moot** / **Superseded** with one-line pointer to D-3 or this plan |
| Tests | `pyproject.toml` declares `testpaths = ["tests"]` but **no** `tests/` Ollama fixtures found in tree snapshot | When test suite exists: add regression tests that Ollama node class names are absent and imports resolve; no string `ollama_native` in provider dicts from pack nodes |
| Other docs | `docs/text_gen_processing_concept.md`, `docs/reference/*` if they mention Ollama nodes | grep and align or archive |

## 3. Phased checklist

**Phase A — Tests & docs (can land before or with code)**

- [x] Update README, CHANGELOG, CLAUDE.md for post-Ollama surface.
- [x] Add/adjust automated tests (when present) for import graph and missing node types.
- [x] Grep whole repo for `ollama`, `Ollama`, `ollama_native`, `LLMProviderOllama`, `/models/ollama`.

**Phase B — Code removal**

- [x] Remove nodes, adapter, endpoint, `_fetch_models_ollama`, JS provider entry, `config.example.yaml` block, `__init__.py` mappings.
- [x] Run ComfyUI load smoke (or minimal `python -c` import of pack) to catch leftover imports.
- [x] Bump **semver** minor or major per project policy; breaking change for saved workflows using Ollama nodes.

**Phase C — Tracker / direction**

- [x] Promote **D-3** to **Decided** once removal ships; update **A-16**, **S-2**, **S-4**, etc., so “supported backends” matches code.
- [x] Optional: short log row in tracker § Log linking this file.

## 4. User migration

Saved workflows that reference **LLM Provider: Ollama** or **LLM Options: Ollama (Core|Extra)** will **break** (missing node types) after upgrade. Users who need native Ollama in ComfyUI should install a **dedicated Ollama custom node pack** and rebuild graphs around that pack’s nodes, or point **LLM Provider: OAI Compatible** at an OpenAI-compatible endpoint if their stack exposes one. Ship the removal with a **semver bump** and **CHANGELOG** entry calling out the breaking change.

## 5. Risks

| Risk | Mitigation |
|------|------------|
| **Broken workflows** | Clear CHANGELOG + README; semver signal; optional migration note listing removed class names |
| **Stale imports / dead routes** | Phase A grep + import smoke after file deletes |
| **Stale tracker rows** | Phase C reconciliation so implementers are not misled by old “three local backends” language |
| **User `config.yaml` still has `providers.ollama`** | Harmless if unused; deep-merge keeps unknown keys—document optional manual deletion |
