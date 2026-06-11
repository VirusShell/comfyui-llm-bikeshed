# Textgen (oobabooga/textgen) lifecycle-related API — verified from upstream

**Date:** 2026-05-12 (initial upstream read); structure backfilled 2026-06-08  
**Scope:** HTTP routes used by this pack for Textgen model memory and model listing, plus auth split. Sources are **upstream application code** on GitHub (`oobabooga/textgen`, formerly “text-generation-webui” lineage), not third-party wikis.

Write-time rules: [`provenance-and-reverification.md`](provenance-and-reverification.md). Template: [`research-note-template.md`](research-note-template.md).

---

## Summary — what we believe

- Textgen splits auth by route: **API key** (`--api-key`) gates chat, `GET /v1/internal/model/info`, and `POST /v1/internal/stop-generation`; **admin key** (`--admin-key`) gates `model/list`, load, and unload when each flag is set.
- At server startup, if only `--api-key` is set, Textgen **copies** it to `admin_key` — admin routes then accept the same bearer. Distinct keys require passing both flags explicitly.
- When a key flag is unset, the corresponding `verify_*` check is a no-op (no auth required for that gate).
- OAI `GET /v1/models` reflects the **loaded** model only; the disk catalog is `GET /v1/internal/model/list`.
- `POST /v1/internal/model/load` always calls `unload_model()` before loading; unload returns 500 on failure.
- `POST /v1/internal/stop-generation` sets `shared.stop_everything`; the generation loop checks it during streaming and non-streaming inference.

---

## Verification

| Topic | Source URL | Access date | Status / commit | Verified how |
|-------|------------|-------------|-----------------|--------------|
| Route registration, `Depends` per path, startup key copy | https://github.com/oobabooga/textgen/blob/main/modules/api/script.py | 2026-06-08 | `main` | code read |
| Current model payload helpers | https://github.com/oobabooga/textgen/blob/main/modules/api/models.py | 2026-05-12 | `main` | code read |
| Response shapes (`ModelInfoResponse`, `LoadModelRequest`) | https://github.com/oobabooga/textgen/blob/main/modules/api/typing.py | 2026-05-12 | `main` | code read |
| Stop-generation + generation loop | `script.py` + `modules/text_generation.py` | 2026-06-07 | `main` | code read |
| Pack wiring (`on_interrupt` → stop-generation) | `adapters/oai_compat.py` | 2026-06-08 | repo | code read |

---

## Applies to

- **Files:** `adapters/oai_compat.py`, `model_list.py`, `server/endpoints.py`, `nodes/providers.py`, `nodes/lifecycle.py`
- **Tracker:** A-19, API-6, API-7
- **Features:** Textgen lifecycle, model dropdown, cancel/interrupt, API vs admin Bearer split

---

## Falsifiers — what would prove this wrong

- `GET /v1/internal/model/info` starts requiring admin bearer while API key is set and differs (or the reverse for list/load/unload).
- `POST /v1/internal/stop-generation` removed, renamed, or moved behind `check_admin_key`.
- Startup key copy removed — admin routes require explicit `--admin-key` even when only `--api-key` is passed.
- `GET /v1/models` begins returning the full disk catalog instead of loaded-only (or empty when idle).
- `LoadModelRequest` required field renamed away from `model_name`.
- Chat route gains an explicit idle-model guard with stable 4xx — would change the partial “idle chat” claim below.

---

## Re-check triggers

Re-open this note when any of these occur:

- [ ] Touching code or docs listed in **Applies to**
- [ ] Upstream `oobabooga/textgen` release or `main` change in `modules/api/script.py`, `models.py`, or `typing.py`
- [ ] Empirical failure on live Textgen (401 with correct key, cancel not stopping, wrong loaded model label)
- [ ] Tracker promotion toward **Confirmed** for Textgen lifecycle, API-6, or API-7
- [ ] Internal route prefix change (`/v1/internal/model/*`, `/v1/internal/stop-generation`)

---

## Confirmed behavior

### Authentication: `--api-key` vs `--admin-key`

In `modules/api/script.py`, `verify_api_key` compares `Authorization: Bearer …` to `shared.args.api_key`. `verify_admin_key` compares to `shared.args.admin_key`. If the corresponding flag is unset, the check is a no-op (no key required).

At server startup (`run_server()`), when `--api-key` is set and `--admin-key` is not, Textgen sets `shared.args.admin_key = shared.args.api_key` — so a single-key deployment uses the same bearer for both gates.

- **Chat and most “user” OAI-style routes** use `dependencies=check_key` → **API key** when configured. Example: `POST /v1/chat/completions` (`check_key`).
- **`GET /v1/internal/model/info`** uses `dependencies=check_key` → **API key** when configured (not the admin key).
- **`GET /v1/internal/model/list`**, **`POST /v1/internal/model/load`**, **`POST /v1/internal/model/unload`** use `dependencies=check_admin_key` → **admin key** when configured.

**Implication:** If a user sets **different** values for `--api-key` and `--admin-key`, clients must send the **API** bearer for `model/info` and chat, and the **admin** bearer for internal list/load/unload. Sending only the admin key on `model/info` fails when an API key is set and differs.

### `POST /v1/internal/stop-generation`

Calls `stop_everything_event()` (sets `shared.stop_everything = True`), which the generation loop checks during both streaming and non-streaming inference. Registered with `dependencies=check_key` → **API key** when configured (same gate as chat).

**Pack wiring re-check:** 2026-06-08 — `adapters/oai_compat.py` `on_interrupt` → `_stop_generation_textgen` → `POST /v1/internal/stop-generation` (verified how: `code read`; applies to cancel-interrupt Tier 2).

### `GET /v1/internal/model/info`

Handler returns `OAImodels.get_current_model_info()`, which (in `models.py`) includes at least `model_name` (from `shared.model_name`), plus `lora_names` and `loader`. This is suitable for discovering **which model is currently loaded** (subject to `model_name` representing “none” when idle — see unknowns).

### `GET /v1/internal/model/list`

Returns `{"model_names": [...] }` from `list_models()` — names available on disk / in the UI catalog, **not** the same as “loaded right now.”

### `POST /v1/internal/model/load`

Body is a `LoadModelRequest`: required **`model_name`** (string); optional `args`, `instruction_template`, `instruction_template_str`. Implementation calls `unload_model()` before loading the requested checkpoint.

### `POST /v1/internal/model/unload`

Calls `unload_model()`; returns `500` with detail `"Failed to unload the model."` on exception.

### `GET /v1/models` (OpenAI-style list)

`list_models_openai_format()` returns OpenAI-style `data`: if `shared.model_name` is set and not the string `'None'`, it returns one entry for that id; **otherwise `data` is an empty list**. So the OAI model list reflects **loaded** model only (often empty when nothing is loaded), unlike `internal/model/list`.

## Partially confirmed / operational

### `POST /v1/chat/completions` when no model is loaded

The route is registered with `check_key` only; there is **no** route-level guard in `script.py` that rejects chat when idle. Actual behavior when `shared.model` is missing depends on the generation stack (`modules/api/completions.py` / `generate_reply`), which this note does **not** fully trace — treat “exact HTTP status and error JSON when idle” as **runtime-dependent** until reproduced on a live instance.

## Unknown / version-sensitive

- Exact error codes and messages from `chat/completions` when no weights are loaded (may vary by loader and version).
- Whether older forks (pre-rename `text-generation-webui`) used identical `Depends` mapping; **this pack should target current `oobabooga/textgen` behavior** and treat older blogs/wiki pages as non-authoritative.

## Audit vs this repository

**Historical (2026-05-12):** The table below recorded gaps before alignment; current code uses **API** bearer for `GET /v1/internal/model/info` and chat, **admin** bearer for `internal/model/list` and load/unload in `adapters/oai_compat.py`; `get_textgen_auth_keys` / `config.example.yaml` document the split; model list resolution uses `model/info` for the loaded label when an API key is available.

| Area | Was (fixed) |
|------|-------------|
| `adapters/oai_compat.py` | `_ensure_model_loaded` briefly used admin-priority for `model/info` — **fixed:** `info_headers` from `_auth_headers`, load/unload from `_admin_headers`. |
| Docstrings / example config | Wording implied one key for all internal routes — **fixed** to distinguish API vs admin gates. |
| UX | **Addressed:** loaded model and backend readouts on the OAI-compat provider (`loaded_model` JSON + `model_dropdown.js` widgets `detected_backend`, `loaded_model_status`); PromptServer path uses parallel Textgen internal list + `model/info` when the backend is Textgen. **Dedicated Textgen provider:** **LLM Provider: Textgen** uses `POST /llm-bikeshed/models/textgen` (no `detect_backend`) and **`manage_model_memory`** on-node for the same load/unload behavior as wiring **LLM Lifecycle: Textgen** into OAI Compatible. |

## Appendix: VRAM control in this pack (today)

This is a snapshot of **what actually runs over the network** for VRAM-related behavior; it is not a product commitment for future lifecycle UX.

- **Textgen (oobabooga/textgen):**
  - **List / loaded hint:** `GET /v1/internal/model/list` (admin bearer when required), `GET /v1/internal/model/info` (API bearer when required) — used by the model dropdown and `loaded_model_status`.
  - **Load before chat:** `POST {url}/v1/internal/model/load` is invoked by the **OpenAI-compatible adapter** when the provider has Textgen lifecycle enabled (**Manage model memory** on **LLM Provider: Textgen**, or **LLM Lifecycle: Textgen** → **OAI Compatible**), not via a separate PromptServer “load” button.
  - **Generation:** `POST {url}/v1/chat/completions` (OAI-compat).
  - **Cancel / stop inference:** on ComfyUI Cancel during chat, adapter calls `POST /v1/internal/stop-generation` (API bearer when required) before aborting the client read.
  - **Explicit unload / chain policy:** when Textgen lifecycle is enabled on the provider (**Manage model memory** on **LLM Provider: Textgen**, or **LLM Lifecycle: Textgen** wired to **OAI Compatible** and ON), the adapter uses `POST /v1/internal/model/unload` (and load when needed) per adapter logic; generation nodes support **`skip_unload`** so only the last node in a chain triggers unload when that design is in use.
- **LM Studio:** TTL / context and related behavior are driven by the **LM Studio lifecycle** node and adapter paths — see [`lm-studio-lifecycle-verified.md`](lm-studio-lifecycle-verified.md) (not the Textgen internal routes above).
- **Ollama:** This pack does **not** ship native Ollama nodes or `/api/chat`; use another pack or an OAI-compatible gateway.
- **What we still need (honest):** Product direction treats heavy **lifecycle manager** UX as under review (`docs/proposals/product-direction-and-scope.md`). Today you have: optional lifecycle nodes, integrated Textgen provider, adapter hooks, and `skip_unload` — not necessarily the final mental model for “VRAM management” in Comfy graphs.
