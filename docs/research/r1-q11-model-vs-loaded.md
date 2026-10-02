# R-1 / Q11 — selected `model` vs loaded model

**Date:** 2026-09-30  
**Scope:** What “the model the user picked” and “the model that is loaded” mean on each host this pack targets, and what that implies for a future loaded→default sync. **Docs only. Do not implement select→default sync, Q11 UI, load-on-select, a version bump, or a registry publish.**

**Product stance for this pass (do not reopen):** Q11 is **select-always**. The graph’s `model` is what generate sends. Syncing a host’s loaded id into the default on local hosts is a **future design** (research, then an overhaul). This note is the research. It is not a green light.

**Supersedes:** [`2026-09-28-model-vs-loaded-per-backend.md`](2026-09-28-model-vs-loaded-per-backend.md) (written at pack `052327f`, before Q6 and A-25). Use this file.

Write-time rules: [`provenance-and-reverification.md`](provenance-and-reverification.md). Template: [`research-note-template.md`](research-note-template.md). Related, still valid for their own routes: [`textgen-lifecycle-verified.md`](textgen-lifecycle-verified.md), [`lm-studio-lifecycle-verified.md`](lm-studio-lifecycle-verified.md).

Pack code read at `db7eb4879269c1f433f40c023d52e414e145c944` (`db7eb48`). No live host was probed.

---

## Summary — what we believe

- In this pack, **`model` is the request id**. It is the Connection / provider widget, then `LLM_PROVIDER["model"]`, then the chat JSON field `"model"`. **`loaded_model` is status JSON** for a read-only widget. Refresh does not copy `loaded_model` into `model`. Model pick does not load weights (Q6).
- Hosts do not share one “loaded” concept:
  - **Textgen** separates the on-disk catalog from the single loaded checkpoint. The chat `model` field does not switch checkpoints.
  - **LM Studio** lists downloaded models and, separately, zero or more `loaded_instances`. Chat can JIT-load. Explicit load is a different call.
  - **llama.cpp single-model** (`llama-server -m …`) has one process model. There is no separate load API. The chat `model` string is not how weights are chosen.
  - **llama.cpp router** (no `-m`) lists many models with `status.value`. The chat `model` field is the route key and, by default, autoloads. `POST /models/load` is a separate act.
  - **OpenAI cloud, and a generic cloud that only speaks the OpenAI models/chat shape, has no loaded-model field.** Naming `model` on chat *is* the selection.
- A future sync that **always** writes `loaded_model` over a saved selection is unsafe on every local host that can have a selected id and a different resident id. A narrower “fill an empty/placeholder widget from a real loaded id” is the only shape that stays compatible with select-always. Even that is not specified here as a build task.

---

## Verification

| Topic | Source URL / path | Access date | Status / commit | Verified how |
|-------|-------------------|-------------|-----------------|--------------|
| Pack select vs status vs generate load | `model_list.py`, `server/endpoints.py`, `nodes/providers.py`, `adapters/oai_compat.py`, `js/llm_connection.js`, `js/model_dropdown.js`, `detection.py` | 2026-09-30 | pack `db7eb48` | `code read` |
| Textgen catalog, loaded, load, chat `model` | https://github.com/oobabooga/textgen/blob/c93f88712395/modules/api/models.py , `script.py`, `typing.py`, `completions.py` (`main` @ `c93f88712395`, 2026-08-17) | 2026-09-30 | `main` @ `c93f887` | `code read` |
| LM Studio list / load / OAI list / chat / JIT | https://lmstudio.ai/docs/developer/rest/list , https://lmstudio.ai/docs/developer/rest/load , https://lmstudio.ai/docs/developer/openai-compat/models , https://lmstudio.ai/docs/developer/openai-compat/chat-completions , https://lmstudio.ai/docs/developer/core/ttl-and-auto-evict | 2026-09-30 | live docs | `docs only` |
| llama.cpp single-model vs router | https://github.com/ggml-org/llama.cpp/blob/db00347a4b33/tools/server/README.md ; `tools/server/server.cpp`, `server-context.cpp`, `server-models.cpp` (`master` @ `db00347a4b33`, 2026-09-30) | 2026-09-30 | `master` @ `db00347` | `code read` |
| OpenAI list + chat `model` | https://developers.openai.com/api/reference/resources/models/methods/list/ , https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create | 2026-09-30 | live reference | `docs only` |
| Live hosts (OOM, `--no-models-autoload`, idle Textgen chat) | — | — | — | **not done** |

`docs only` is not enough to mark a tracker row Confirmed or to ship sync.

---

## Applies to

- **Files:** `model_list.py`, `server/endpoints.py`, `nodes/providers.py`, `adapters/oai_compat.py`, `detection.py`, `js/llm_connection.js`, `js/model_dropdown.js`
- **Worklist:** R-1 / Q11 (research landed; implementation stays ask-first)
- **Features:** Connection model widget, `loaded_model` status, Manage VRAM, generate-time load. Not Options merge, not node unregister, not llama.cpp router client work.

---

## Falsifiers — what would prove this wrong

- Textgen `ChatCompletionRequest.model` starts loading or switching `shared.model` (today the field text says it is unused).
- Textgen `GET /v1/models` starts returning the disk catalog (`list_models_openai_format` today returns the loaded id or an empty `data` list).
- LM Studio `GET /api/v1/models` drops `models[].key` or `loaded_instances`.
- LM Studio documents that `GET /v1/models` is loaded-only even when JIT is on (today it says the list may include all downloaded models when JIT is enabled).
- llama.cpp router stops serving `GET /v1/models` from `get_router_models`, or drops `status.value`.
- llama.cpp single-model mode starts rejecting chat when `model` ≠ the loaded id.
- OpenAI `GET /v1/models` adds a load/resident field clients must honor.
- This pack’s refresh path writes `loaded_model` into the `model` widget (it does not, at `db7eb48`).

---

## Re-check triggers

- [ ] Editing list, loaded, ensure-loaded, or Connection model JS
- [ ] Textgen `modules/api/models.py` / `typing.py` change the catalog vs loaded split
- [ ] LM Studio REST list or JIT docs change
- [ ] llama.cpp router `/v1/models` diverges from `/models`, or autoload default changes
- [ ] A future Q11 implementation (still ask-first)
- [ ] A live host where chat does not match the matrix below

---

## What the pack does today (select-always)

`loaded_model` never enters the provider dict. Status widgets are `serialize: false`.

| Step | What happens |
|------|----------------|
| **Connection refresh** | `POST /llm-bikeshed/models/connection` → `sync_resolve_connection_models`. Catalog faces (`text_gen_webui`, `lm_studio`, `openai`) return a list plus a `loaded_model` probe. **llama.cpp and generic return `[], backend, None` and do not probe.** `js/llm_connection.js` `updateModelCombo` keeps the current real id if it is still in the list, else the saved value, else the first catalog id. It does **not** read `loaded_model`. |
| **Connection status line** | `loadedStatusLine`. Empty loaded on the OpenAI face, and on non-catalog faces other than Textgen/LM Studio, shows `loaded: n/a`. A non-empty string still renders `loaded: …` (so a sole-id heuristic on the OpenAI face is visible). |
| **Legacy providers** | `js/model_dropdown.js` fills `loaded_model_status` from the same JSON. The model COMBO uses the same “keep current / saved / first” rule, not `loaded_model`. |
| **Model pick** | Both JS files mark the node dirty and return. They do not call `POST /llm-bikeshed/models/ensure-loaded`. No JS caller of that route remains. The route still exists for a direct POST. |
| **Generate** | `adapters/oai_compat.py` `_chat_completion` always sends `"model": <provider model>`. **Textgen** calls `POST /v1/internal/model/load` first when `load_before_generate` is true (Connection Manage VRAM ON, or the flag omitted, which defaults true for Textgen). **LM Studio** calls `POST /api/v1/models/load` only when a lifecycle is embedded (Connection Manage VRAM ON). **llama.cpp, OpenAI, generic:** no pack load or unload. |
| **Ensure-loaded helper** | `sync_ensure_model_loaded`: Textgen internal load, LM Studio `POST /api/v1/models/load`, llama.cpp `POST /models/load`, anything else `"does not support explicit model load"`. Not used by the model widget. |
| **Detection** | `GET /health` JSON with a `status` key → `llamacpp` for both single-model and router (`server.cpp` leaves `get_health` on the router; single-model returns `{"status":"ok"}`). Detection does **not** split router vs classic. Auto+Ollama is forced to the generic face. Ollama is out of this note. |

---

## Per-backend matrix

### Textgen (oobabooga/textgen)

| Question | Answer |
|----------|--------|
| **List available** | `GET /v1/internal/model/list` → `model_names` (disk / UI catalog). Admin key when `--admin-key` is set. |
| **Currently loaded** | `GET /v1/internal/model/info` → `model_name` (API key when `--api-key` is set). Idle is `None` or the string `'None'`. `GET /v1/models` is **loaded-only**: one id, or `data: []` when idle. It is not the catalog. |
| **Select vs load** | **Separate.** Load is `POST /v1/internal/model/load` with `model_name`. That path calls `unload_model()` then loads. One resident checkpoint. |
| **Must chat `model` match the loaded id?** | **No.** `ChatCompletionRequest.model` is documented: “Unused parameter. To change the model, use the `/v1/internal/model/load` endpoint.” Completions pop `model` and answer with `shared.model_name`. A mismatched id does not swap weights. |
| **Pack** | Catalog from internal list; `loaded_model` from `model/info`, but **only if an API key is configured** (`_fetch_textgen_loaded_model_from_info` returns `None` with no key). Manage VRAM ON loads the **selected** id before chat and unloads after the chain. OFF sends chat only, so the resident checkpoint answers, whatever the widget says. |
| **No loaded concept?** | It has one. Do not pretend `GET /v1/models` is the picker list. |

### LM Studio

| Question | Answer |
|----------|--------|
| **List available** | REST `GET /api/v1/models` → `models[]` with `key` (downloaded LLMs and embeddings). OAI `GET /v1/models` is “models visible to the server” and **may include all downloaded models when JIT is on**. That OAI list is not a loaded set. |
| **Currently loaded** | REST `loaded_instances[]` on each model (`id`, `config.context_length`, …). Empty array means that key is not loaded. Several keys can have instances at once. |
| **Select vs load** | **Separate.** `POST /api/v1/models/load` body `model` (optional `context_length`, …) returns `instance_id` and `status: "loaded"`. Unload is `instance_id`, not the key. Chat `model` is the identifier; with JIT on (default), the **first request loads** that model. TTL default for JIT is 60 minutes. Auto-Evict (default on) keeps at most one **JIT** model; models loaded outside JIT are not evicted by that switch. |
| **Must chat `model` match a loaded id?** | It must name a model the server knows. It does **not** have to be loaded already when JIT is on. Explicit load is how this pack sets `context_length` before chat. |
| **Pack** | Dropdown ids come from `GET /v1/models`. Status takes the **first** `key` with a non-empty `loaded_instances` (one string, not the instance id). Manage VRAM ON embeds lifecycle: ensure-load (reload if context length mismatches) plus `ttl` on the chat body. OFF embeds nothing: no pack load, no TTL; host JIT can still load. |
| **No loaded concept?** | It has one, on the REST list, and it can be plural. |

### llama.cpp — single model (`llama-server -m`)

| Question | Answer |
|----------|--------|
| **List available** | `GET /v1/models` and `GET /models` share one handler. The body has **one** `data[]` element: `id` is the model name (`-m` path, or `--alias`). There is **no** `status` object. |
| **Currently loaded** | That single id. The process loaded it at startup. There is no “selected but not loaded” state. |
| **Select vs load** | **Same act as starting the process.** Router routes `POST /models/load` and `POST /models/unload` are registered only when `is_router_server`. |
| **Must chat `model` match the loaded id?** | **No.** Router docs say the chat `model` field is the route key; single-model mode does not use it that way. Official chat examples send `gpt-3.5-turbo` against a GGUF. The control endpoint’s `model` field is documented “Ignored in single model mode.” `oaicompat_chat_params_parse` does not check the string. The response may echo the request’s `model`. |
| **Pack** | Both modes fingerprint as `llamacpp`. Connection therefore uses **free text**, returns **`loaded_model: null`**, and hides Manage VRAM. Chat sends the typed id and does not call `/models/load`. The legacy OAI provider path does call `GET /v1/models` and, if there is no `status.value == "loaded"` and **exactly one** id, reports that id as `loaded_model`. That heuristic matches this mode. |
| **No loaded concept?** | There is no second “loaded” field. The only id **is** the loaded model. |

### llama.cpp — router (no `-m`; cache, `--models-dir`, or `--models-preset`)

| Question | Answer |
|----------|--------|
| **List available** | `GET /models` **and** `GET /v1/models` both call `get_router_models` (`server.cpp`). Each row has `id`, `aliases`, and `status.value` of `unloaded`, `loading`, `loaded`, `sleeping`, `downloading`, or a failed unload. This is the catalog, not a loaded-only list. |
| **Currently loaded** | `status.value == "loaded"`. `sleeping` is still a running child (“new request will wake it up”). Several rows can be `loaded` up to `--models-max` (default 4; `0` = unlimited). LRU unload applies when the cap is hit. |
| **Select vs load** | **Separate, but chat also loads.** `POST /models/load` with `{"model": "<id>"}` returns `{"success": true}` when the name exists and is not already running. The handler calls `models.load` and returns; it does not wait for `loaded`. `get_meta` accepts the id or an alias. Chat `POST /v1/chat/completions` routes on the JSON `model` field. **Autoload is on by default** (`--models-autoload`): a request for an unloaded id loads it. `--no-models-autoload` disables that. Per-request `?autoload=true\|false` exists. Preset `load-on-startup` is a third, startup-only switch. |
| **Must chat `model` match a loaded id?** | It must name a known id or alias. With autoload on, it does not have to be loaded yet. With autoload off, an unloaded id is not started by the request. |
| **Pack** | Connection still does not list or report loaded state (same face as single-model). Legacy OAI path parses `data[].status.value == "loaded"` and keeps the **first** such id. If none match and the list length is 1, the sole-id fallback reports that id as loaded **even when `status.value` is `unloaded`**. Generate does not call `/models/load`. `sync_ensure_model_loaded` would, and treats HTTP 200 as success, which on this host means “accepted,” not “status is loaded.” The adapter has no unload. |
| **No loaded concept?** | It has one: `status.value`. It is not the chat `model` field, and it is not a single slot. |

### OpenAI cloud and generic OpenAI-compatible cloud

| Question | Answer |
|----------|--------|
| **List available** | `GET /v1/models` → `data[]` of `{id, created, object: "model", owned_by}`. “Currently available models” for the account. |
| **Currently loaded** | **No such field.** The Model object has no resident/loaded/status property. |
| **Select vs load** | **The same client act.** There is no public load or unload API. `POST /v1/chat/completions` `model` is “Model ID used to generate the response.” |
| **Must chat `model` match a loaded id?** | It must be an id the account can call. “Loaded” is not a client-visible state. |
| **Pack** | Face `openai` (detection fell through to a live `GET /v1/models`) is a **catalog** COMBO. The same resolver still runs the llama.cpp loaded parser: `status.value == "loaded"`, else **the only id in the list**. An account with one model id therefore gets `loaded_model` set to that id, and Connection will show `loaded: <id>` because the `n/a` branch only runs when the string is empty. That string is not VRAM. Face `generic` (nothing detected, or Auto+Ollama remapped) is free text and Connection forces `loaded_model` to `None`. Neither face has Manage VRAM. Generate is chat only. |
| **No loaded concept?** | **Yes. Say so.** Do not invent one from a one-element catalog. Some other servers that speak `/v1/chat/completions` (a single-model vLLM, classic llama.cpp) *do* have one resident model, but that is their product, not the OpenAI list schema. This pack cannot see the difference once detection has labeled the host `openai` or `generic`. |

Ollama is out of scope.

---

## Future sync — what would be safe, what would not

Do **not** build this yet. Select-always stays: a saved or typed `model` is what generate sends. Loaded state may be shown. It must not silently replace that choice.

Always-overwrite (refresh copies `loaded_model` onto a real widget value) is unsafe everywhere it can disagree with the user:

| Host | Why always-overwrite is unsafe | What a later design could consider | What it must not do |
|------|--------------------------------|------------------------------------|---------------------|
| **Textgen** | User can stage the next catalog id while another checkpoint is resident. Overwrite puts the old id back. The next Manage-VRAM generate then reloads that old id (`unload_model()` then load) and drops the staged choice. `loaded_model: null` also means “no API key,” not only “VRAM idle.” | Fill a **placeholder** widget only when `model/info` returned a real name that is in the catalog. Keep an explicit “use loaded” action if someone asks for it. | Treat null as “clear the combo.” Treat `GET /v1/models` as the catalog. Assume the chat `model` field swaps weights when Manage VRAM is off. |
| **LM Studio** | “First key with `loaded_instances`” is arbitrary when more than one model is loaded. Auto-Evict does not cover non-JIT loads. Overwrite fights a user who picked an unloaded key for JIT on the next chat. | Placeholder fill only when **exactly one** key has instances, and that key is in the dropdown. | Sync to the first of many. Treat `GET /v1/models` as the loaded set. Load on select. |
| **llama.cpp single-model** | Low second-load risk: chat does not load a different GGUF. Overwrite can still replace a typed alias/path the user meant to keep. Connection does not fetch the id today, so there is nothing honest to copy on that face. | If a later probe sees one `data[]` id and **no** `status` object, that id is the process model. Filling an **empty** free-text box is the least sharp option. | Run that fill on a router body. Call `/models/load` (the route is absent in this mode). |
| **llama.cpp router** | Overwrite plus the next chat **autoloads** the copied id (default) or keeps it resident beside others until `--models-max`. That is a second load / eviction, not a label change. The pack’s sole-id fallback labels a single **unloaded** row as loaded. `sleeping` is resident and the pack ignores it. `POST /models/load` success is “accepted,” not “loaded.” | Read `status.value`. If a probe is ever shown on the Connection face, show loaded vs sleeping vs not. Placeholder fill only for exactly one `loaded` or `sleeping` row, and do not load as part of the fill. | Copy “first loaded” when several are loaded. Treat sole-id-without-checking-status as loaded. Assume generate calls `/models/load` (it does not). Assume autoload is on (`--no-models-autoload` is invisible to the pack). |
| **OpenAI / generic cloud** | There is no loaded model. The sole-id heuristic on the OpenAI face is a catalog accident. Writing it into the combo changes which hosted model is billed and called. | Leave the widget user-owned. Keep showing `loaded: n/a` unless a non-standard `status.value` is actually present — and still do not sync it on this face. | Any loaded→default sync. |

Placeholder-only fill is still a product change. It can load a large checkpoint on the **next** generate (Textgen Manage VRAM ON, LM Studio JIT or Manage VRAM ON, llama.cpp router autoload) if the empty widget would otherwise have stayed empty or stayed on another default. That is why it stays ask-first.

---

## Confirmed (code or pinned upstream)

- Pack refresh does not copy `loaded_model` into `model`. Model pick does not call ensure-loaded.
- Textgen list vs info vs unused chat `model` vs load-unloads-first, at `oobabooga/textgen` `c93f887`.
- LM Studio REST `key` / `loaded_instances` vs OAI list wording vs separate load vs JIT, from the docs pages dated above.
- llama.cpp: one models handler per mode; router `status.value`; chat autoload default; `/models/load` returns before the child is loaded; single-model payload has no `status`.
- OpenAI list schema has no load field. Chat `model` is the model id.

## Partially confirmed

- Textgen chat when `shared.model` is missing: the route has no idle guard in `script.py`. The exact error from the generation stack was not re-traced in this pass.
- LM Studio JIT vs explicit `context_length` still depends on the older open issue cited in `lm-studio-lifecycle-verified.md`. Not re-fetched here. The TTL page is enough to say JIT loads on first chat.
- llama.cpp single-model “model string ignored” is the README control-endpoint sentence, the dummy id in the chat examples, and the absence of a check in `oaicompat_chat_params_parse`. Not an end-to-end run.

## Unknown (needs a live host)

- OOM when a selected id and a resident id differ, on Textgen and on a router with `--models-max 1`.
- Router chat with `--no-models-autoload` and an unloaded id (expected failure; not captured).
- Whether a given generic gateway adds its own `status` object. The OpenAI schema does not.

---

## Non-goals

- No select→default sync, no Connection UI change, no `LLM*` class ID rename.
- No version bump, no registry publish, no llama.cpp router client, no Manage VRAM behavior change.
