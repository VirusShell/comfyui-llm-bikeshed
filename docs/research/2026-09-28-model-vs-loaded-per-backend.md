# model vs loaded_model per backend — research (Q11 / R-1)

**Date:** 2026-09-28  
**Scope:** Per-backend reality for selectable model list vs loaded status vs when this pack triggers a load (Textgen, LM Studio, llama.cpp router vs classic, OpenAI cloud). Propose a common rule that lets the user select a model without accidental second load / OOM. **Docs only — no sync implementation.**

Write-time rules: [`provenance-and-reverification.md`](provenance-and-reverification.md). Template: [`research-note-template.md`](research-note-template.md). Systems map: [`2026-09-27-pack-systems-map.md`](2026-09-27-pack-systems-map.md) (Q11). Related: [`textgen-lifecycle-verified.md`](textgen-lifecycle-verified.md), [`lm-studio-lifecycle-verified.md`](lm-studio-lifecycle-verified.md). Pack tip at write: `052327f`.

---

## Summary — what we believe

- **`model`** is request identity (COMBO / free-text → `LLM_PROVIDER["model"]` → chat payload `"model"`). **`loaded_model`** is status chrome only (JS `serialize:false`); refresh never copies it into `model` today.
- Backends differ sharply: Textgen separates disk catalog vs loaded; LM Studio catalogs all keys and marks loaded instances; llama.cpp **router** catalogs many with `status.value`; classic single-model llama.cpp often exposes one id; OpenAI cloud catalogs callable ids with **no local “loaded”**.
- Pack load fires today on: (1) **generate** when `load_before_generate` / LM lifecycle says so; (2) **optional select-path** via `ensure_load_on_select` (Connection) or `model_dropdown.js` load-on-select (legacy providers); (3) **not** on URL refresh alone. Vir Q6 locks (1)/(Manage VRAM) only — select preload is to be ripped (WORKLIST first code stream).
- **Reject naive always-sync combo → loaded on status.** Auto-writing the combo from status undoes user intent and, if any select-load path remains (or generate then loads the overwritten id while another weight is resident), risks a **second load / OOM** on single-slot or VRAM-tight hosts.
- **Recommended common rule:** user owns selection; status may hint mismatch; never mutate combo from `loaded_model`; load only on generate (policy ON) or explicit Manage VRAM — never on select.

---

## Verification

| Topic | Source URL / path | Access date | Status / commit | Verified how |
|-------|-------------------|-------------|-----------------|--------------|
| Pack list / loaded / ensure-loaded | `model_list.py`, `server/endpoints.py` | 2026-09-28 | tip `052327f` | `code read` |
| Select preload + status chrome | `js/llm_connection.js`, `js/model_dropdown.js` | 2026-09-28 | tip `052327f` | `code read` |
| Generate-time load / unload | `adapters/oai_compat.py`, `nodes/providers.py` | 2026-09-28 | tip `052327f` | `code read` |
| Textgen catalog vs loaded / load | [`textgen-lifecycle-verified.md`](textgen-lifecycle-verified.md); upstream `oobabooga/textgen` API | 2026-06-08 / 2026-09-28 | prior note | `code read` (pack + prior upstream) |
| LM Studio list / load / JIT | [`lm-studio-lifecycle-verified.md`](lm-studio-lifecycle-verified.md); https://lmstudio.ai/docs/developer/rest/list ; https://lmstudio.ai/docs/developer/rest/load ; https://lmstudio.ai/docs/developer/core/ttl-and-auto-evict | 2026-06-07 / 2026-09-28 | prior note + docs | `docs only` + pack `code read` |
| llama.cpp router model management | https://huggingface.co/blog/ggml-org/model-management-in-llamacpp | 2026-09-28 | published 2025-12-11 | `docs only` |
| OpenAI list models | https://developers.openai.com/api/reference/resources/models/methods/list/ | 2026-09-28 | current docs | `docs only` |
| Live host probes (multi-slot OOM, classic sole-id edge) | — | — | — | **not done** — needs Vir/host |

---

## Applies to

- **Files:** `model_list.py`, `server/endpoints.py`, `js/llm_connection.js`, `js/model_dropdown.js`, `adapters/oai_compat.py`, `nodes/providers.py`, systems map Q11
- **Tracker / worklist:** R-1 / Q11; Q6 preload rip (separate implementable stream)
- **Features:** Connection / provider model COMBO, `loaded_model` status, ensure-loaded, generate-time ensure

---

## Falsifiers — what would prove this wrong

- A backend where listing models always loads weights (then “select without load” is impossible without a different list API).
- OpenAI (or a cloud gateway) returning a meaningful local `status.value == loaded` that clients must follow for correctness.
- Pack code path that already copies `loaded_model` into the `model` widget on refresh (would contradict “status-only today”).
- Router llama.cpp with `--no-models-autoload` where chat never loads without `/models/load` — would tighten when “generate alone” is enough.

---

## Re-check triggers

- [ ] Touching list/loaded/ensure-loaded or Connection model JS
- [ ] Textgen / LM Studio / llama.cpp / OpenAI API shape change for models list or load
- [ ] Implementing or rejecting any `model`↔`loaded_model` sync UX
- [ ] Q6 preload rip landing (select-path rows below go stale)
- [ ] Empirical OOM when combo ≠ loaded on single-slot host

---

## Per-backend matrix (pack code + cited host docs)

### Textgen (oobabooga/textgen)

| Concern | Reality |
|--------|---------|
| **Selectable list** | Pack prefers `GET /v1/internal/model/list` → `model_names` (disk/UI catalog). OAI `GET /v1/models` is **loaded-only** (empty when idle) — poor catalog; pack falls back after internal list. |
| **Loaded status** | `GET /v1/internal/model/info` → `model_name` (API-key gate when set). Normalized to `None` when idle/`None`. |
| **When pack triggers load** | **Generate:** `_ensure_model_loaded` when `load_before_generate` (Connection Textgen face + Manage memory ON; Textgen provider toggle; OAI Compatible defaults `load_before_generate` True at Textgen URLs). **Select:** Connection if `ensure_load_on_select` ON; legacy dropdown if manage-memory widget ON (or Textgen OAI path without mem widget). **Lifecycle unload** after chain when lifecycle present and not `skip_unload`. |
| **OOM if combo auto-follows loaded** | Single-slot: sync would usually **match** after a successful load, but would **clobber** a user who picked the *next* model while another is still loaded — then generate/select-load of the synced id is fine, but sync *away* from the intended next id forces an extra load later or undoes planning. Sync **to** a stale loaded id while user selected a different large checkpoint, combined with residual select-load, can start a second load before unload completes. |

Host detail (prior note): load always `unload_model()` then load; admin vs API key split for list/load vs info/chat.

### LM Studio

| Concern | Reality |
|--------|---------|
| **Selectable list** | Pack uses OAI-compat `GET /v1/models` for dropdown ids; loaded probe uses REST `GET /api/v1/models` → first `models[].key` with non-empty `loaded_instances`. |
| **Loaded status** | REST `loaded_instances[]` (may be multi-instance). Pack status takes **first** loaded key only. |
| **When pack triggers load** | **Generate:** `_ensure_model_loaded_lm_studio` when lifecycle type `lm_studio` (Connection LM face **always** embeds lifecycle today; OAI + Lifecycle LM). May reload if `context_length` mismatches. TTL on chat payload. **Select:** Connection `ensure_load_on_select`; legacy dropdown only if a manage-memory widget is ON (OAI Compatible has **no** mem widget → **no** select-load for LM on that path). Host **JIT** may still load on first chat without explicit REST load (docs). |
| **OOM if combo auto-follows loaded** | Multi-load possible; Auto-Evict helps but is not a guarantee under concurrent JIT + explicit load. Syncing combo to “first loaded” in a multi-instance host is **arbitrary** and can deselect the user’s target. Combined with generate ensure + JIT, risk of extra load/evict churn. |

### llama.cpp — router vs classic

| Concern | Reality |
|--------|---------|
| **Detection** | Pack: `GET /health` with `status` → `llamacpp`. Does **not** distinguish router vs classic in `detect_backend`. |
| **Selectable list** | Connection: `catalog=False` for llama.cpp → **empty list**, free-text `model` (no COMBO catalog); `loaded_model` returned **`None`** on Connection llama face. OAI Compatible path: `GET /v1/models` id list. |
| **Loaded status** | Pack parses `data[].status.value == "loaded"` (router-shaped); else if **exactly one** id in `/v1/models`, treats that as loaded (classic sole-model heuristic). |
| **When pack triggers load** | **Generate:** adapter does **not** call llama `/models/load` on chat — relies on host. Router docs: **on-demand load** on first request unless `--no-models-autoload`; explicit `POST /models/load` + `POST /models/unload`. Pack `sync_ensure_model_loaded` → `POST {url}/models/load` for select-path / ensure-loaded when backend `llamacpp`. **Select:** Connection only if `ensure_load_on_select`; OAI dropdown: `llamacpp` is in `LOAD_ON_SELECT_BACKENDS` but without manage-memory widget `shouldLoadOnSelect` is **false** unless backend is Textgen. |
| **Classic** | Single `-m` server: typically one model; chat uses that weight; no router `/models/load`. Sole-id heuristic ≈ “loaded.” |
| **Router (host docs)** | List via `/models` with status; `/v1/models` reflects instance metadata; LRU `--models-max`; optional disable autoload. |
| **OOM if combo auto-follows loaded** | Router multi-model: syncing to one loaded id while user typed another id invites autoload of a second model (up to max) or thrash. Classic: sync is usually redundant; still wrong if status heuristic and typed alias diverge. |

### OpenAI cloud

| Concern | Reality |
|--------|---------|
| **Selectable list** | `GET /v1/models` → `data[].id` (account-available models). Connection treats `openai` as **catalog** backend. |
| **Loaded status** | **No local VRAM “loaded”.** Pack may still run `_fetch_loaded_model_from_oai_models` for backend `openai` (sole-id / status parse); Connection UI **hides** loaded line for `face === "openai"`. Official list models API returns id/created/owned_by — not load state. |
| **When pack triggers load** | **Never** via ensure-loaded (`backend does not support explicit model load`). Generate is just `POST /v1/chat/completions` with `"model"`. |
| **OOM if combo auto-follows loaded** | Local OOM N/A. Sync still harmful: would overwrite user’s chosen model id from a meaningless/sole-id heuristic. |

---

## Pack trigger map (today)

| Trigger | Textgen | LM Studio | llama.cpp | OpenAI |
|---------|--------|-----------|-----------|--------|
| Refresh Models / URL fetch | list + loaded probe only | list + loaded probe | Connection: no catalog/loaded; OAI: list + heuristic | list (+ hidden loaded) |
| Model COMBO/select | optional ensure-loaded | optional ensure-loaded | optional ensure-loaded (Connection widget / ensure route) | no |
| Generate | ensure if `load_before_generate` | ensure if LM lifecycle present | host JIT / already loaded; pack no generate-time `/models/load` | chat only |
| Manage VRAM / lifecycle unload | unload when lifecycle + last in chain | unload / TTL | setup-gated router unload (product); not full adapter parity yet | n/a |

---

## Recommended common rule

1. **`model` is user/graph-owned.** Never auto-write the COMBO or free-text from `loaded_model` / status refresh / external host events.
2. **`loaded_model` is status-only.** May show `loaded: X` and an optional **non-mutating** mismatch hint when `model ≠ loaded` on local hosts that report load state.
3. **Load policy (align Q6):** load weights only when (a) a generate run requires it under Manage VRAM / `load_before_generate` / lifecycle, or (b) an explicit Manage VRAM action — **never** on model pick/select. Rip select preload (WORKLIST first stream).
4. **Do not “fix” mismatch by syncing.** Prefer: user clicks the loaded name into the combo if they want it, or generate loads the selected id (replacing prior weight per host rules).
5. **OpenAI / multi-model cloud:** no loaded sync concept; combo is purely the API model id.
6. **Reject** naive “always sync combo to loaded on status” as a product default.

This allows selecting the next model while another remains loaded (browse catalog, stage graph) without forcing a second resident weight until generate/Manage VRAM.

---

## Confirmed behavior (code-proven)

- Dual surface `model` vs `loaded_model` with no copy-on-refresh (`js/*`, systems map smell).
- Textgen list vs info split and generate-time ensure paths in pack.
- LM Studio REST loaded parse + generate-time ensure when lifecycle present; Connection LM always embeds lifecycle today.
- llama.cpp Connection non-catalog → `loaded_model is None`; ensure-loaded posts `/models/load`.
- OpenAI ensure-loaded rejected; Connection hides loaded line for openai face.
- Select-path ensure-loaded exists and is Q6 rip target.

## Partially confirmed / docs-only (host)

- llama.cpp router autoload / `--no-models-autoload` / `/models` vs `/v1/models` status shapes (HF blog + community; not probed on Vir’s hosts this pass).
- LM Studio JIT + Auto-Evict interaction under pack generate ensure (prior note; issue #1463 open historically).

## Unknown / needs Vir or host test

- Empirical OOM: select different large model while A loaded, with ensure_load ON vs OFF, on Textgen single-slot and llama router `--models-max 1`.
- Classic llama.cpp `/v1/models` multi-id edge cases (LoRA / aliases) vs sole-id loaded heuristic.
- Whether any deployed router build omits `status.value` on `/v1/models` (pack would fall through to sole-id / None).
- Product choice later: offer “Use loaded” **button** (explicit user action) vs hint-only — out of scope for sync implementation here.

---

## Non-goals

- No `model`↔`loaded_model` sync code.
- No Q6 preload rip in this note (tracked on WORKLIST as first implementable stream).
- No version bump.
